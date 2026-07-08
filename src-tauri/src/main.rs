use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

struct BackendProcess(Mutex<Option<Child>>);

fn find_backend() -> PathBuf {
    // 1. Production: Tauri bundled resource (Contents/Resources/)
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
        .unwrap_or_default();

    let name = "agent-hub-backend";

    // macOS .app bundle: binary at Contents/MacOS/, resources at Contents/Resources/_up_/
    let resource_candidates = vec![
        exe_dir.join("../Resources/_up_/pyinstaller-dist").join(name),
        exe_dir.join("../Resources").join(name),
        exe_dir.join("../../Resources/_up_/pyinstaller-dist").join(name),
        exe_dir.join(name),
    ];

    for path in &resource_candidates {
        if path.exists() {
            return path.clone();
        }
    }

    // 2. Development fallback
    let dev_path = PathBuf::from("../pyinstaller-dist").join(name);
    if dev_path.exists() {
        return dev_path;
    }

    // 3. Last resort: assume it's on PATH
    PathBuf::from(name)
}

fn wait_for_backend(addr: &str, max_secs: u64) -> bool {
    for _ in 0..(max_secs * 10) {
        if TcpStream::connect(addr).is_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    false
}

fn try_kill_existing_backend() {
    // On macOS, try to kill any existing agent-hub-backend process
    let _ = Command::new("pkill")
        .args(["-f", "agent-hub-backend"])
        .output();
}

fn main() {
    try_kill_existing_backend();

    // Spawn Python backend before creating the Tauri app
    let backend = find_backend();
    if !backend.exists() {
        eprintln!(
            "Agent Hub backend not found at: {}\n\
             Please build the backend first with: bash scripts/build-backend.sh",
            backend.display()
        );
        std::process::exit(1);
    }

    let mut child = Command::new(&backend)
        .arg("start")
        .arg("--desktop")
        .spawn()
        .unwrap_or_else(|e| {
            eprintln!("Failed to start Agent Hub backend: {}", e);
            std::process::exit(1);
        });

    if !wait_for_backend("127.0.0.1:9527", 15) {
        let _ = child.kill();
        eprintln!("Agent Hub backend failed to start within 15 seconds");
        std::process::exit(1);
    }

    tauri::Builder::default()
        .manage(BackendProcess(Mutex::new(Some(child))))
        .setup(move |app| {
            let _window = WebviewWindowBuilder::new(
                app.handle(),
                "main",
                WebviewUrl::External("http://127.0.0.1:9527".parse().unwrap()),
            )
            .title("Agent Hub")
            .inner_size(1200.0, 800.0)
            .min_inner_size(900.0, 600.0)
            .build()?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<BackendProcess>();
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(ref mut child) = *guard {
                        let _ = child.kill();
                    }
                };
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
