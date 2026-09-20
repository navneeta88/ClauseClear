# Starts the Flask backend and the Vite frontend in two new windows.
$root = $PSScriptRoot
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\venv\Scripts\Activate.ps1; python app.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
Start-Process "http://localhost:5173"