#!/usr/bin/env python3
"""
Test script to measure startup time improvements.
This script measures the time it takes for various parts of the application to load.
"""
import time
import sys

print("=" * 60)
print("STARTUP TIME TEST")
print("=" * 60)

# Test 1: Import time for main components
print("\n[1] Testing import times...")

start = time.time()
from PySide6.QtWidgets import QApplication
pyside_time = time.time() - start
print(f"  PySide6 import: {pyside_time:.3f}s")

start = time.time()
from whisperx.app.transcription_manager import TranscriptionManager
manager_time = time.time() - start
print(f"  TranscriptionManager import: {manager_time:.3f}s")

start = time.time()
from whisperx.app.whisperx_bridge import WhisperXBridge
bridge_time = time.time() - start
print(f"  WhisperXBridge import: {bridge_time:.3f}s")

# Test 2: Check that torch is NOT imported yet
print("\n[2] Verifying lazy loading...")
if 'torch' in sys.modules:
    print("  ❌ FAIL: torch is already imported (lazy loading not working)")
else:
    print("  ✅ PASS: torch is not yet imported (lazy loading working)")

# Test 3: Measure MainWindow creation time
print("\n[3] Testing MainWindow creation...")
start_total = time.time()

app = QApplication(sys.argv)

start_window = time.time()
from whisperx.appSmartVoice.main import MainWindow
import_main_time = time.time() - start_window
print(f"  Import MainWindow: {import_main_time:.3f}s")

start_init = time.time()
window = MainWindow()
init_time = time.time() - start_init
print(f"  MainWindow.__init__: {init_time:.3f}s")

total_time = time.time() - start_total
print(f"\n  TOTAL TIME TO WINDOW DISPLAY: {total_time:.3f}s")

# Test 4: Verify torch is still not imported after window creation
print("\n[4] Verifying torch still not imported after window creation...")
if 'torch' in sys.modules:
    print("  ⚠️  WARNING: torch was imported during window creation")
    print("     (This might be unavoidable if PySide6 or Custom_Widgets uses it)")
else:
    print("  ✅ PASS: torch still not imported")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Total startup time: {total_time:.3f}s")
print(f"  - PySide6 import: {pyside_time:.3f}s ({pyside_time/total_time*100:.1f}%)")
print(f"  - TranscriptionManager import: {manager_time:.3f}s ({manager_time/total_time*100:.1f}%)")
print(f"  - WhisperXBridge import: {bridge_time:.3f}s ({bridge_time/total_time*100:.1f}%)")
print(f"  - MainWindow import: {import_main_time:.3f}s ({import_main_time/total_time*100:.1f}%)")
print(f"  - MainWindow init: {init_time:.3f}s ({init_time/total_time*100:.1f}%)")

if total_time < 5.0:
    print("\n✅ EXCELLENT: Startup time is under 5 seconds!")
elif total_time < 10.0:
    print("\n✅ GOOD: Startup time is under 10 seconds")
else:
    print("\n⚠️  WARNING: Startup time is still slow (>10s)")

print("=" * 60)

# Clean up
window.close()
app.quit()
sys.exit(0)
