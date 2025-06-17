#!/usr/bin/env python3
"""
Lock debugging utilities for BeaconCache deadlock detection.
"""

import threading
import time
import traceback
from typing import Dict, List

def dump_all_thread_stacks():
    """Dump stack traces for all threads - useful for deadlock detection"""
    stacks = {}
    for thread_id, frame in threading._current_frames().items():
        thread = None
        for t in threading.enumerate():
            if t.ident == thread_id:
                thread = t
                break
        
        thread_name = thread.name if thread else f"Thread-{thread_id}"
        stacks[thread_name] = traceback.format_stack(frame)
    
    return stacks

def print_thread_stacks():
    """Print all thread stacks to help identify deadlocks"""
    print("\n" + "="*80)
    print("THREAD STACK DUMP")
    print("="*80)
    
    stacks = dump_all_thread_stacks()
    for thread_name, stack in stacks.items():
        print(f"\nThread: {thread_name}")
        print("-" * 40)
        print("".join(stack))

def monitor_locks(beacon_cache, interval=5):
    """Monitor lock status and detect potential deadlocks"""
    print(f"Starting lock monitor (checking every {interval}s)")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            print(f"\n[{time.strftime('%H:%M:%S')}] Lock Status:")
            print("-" * 50)
            
            # Print lock status
            status = beacon_cache.debug_lock_status()
            print(status)
            
            # Count active threads
            active_threads = [t for t in threading.enumerate() if t.is_alive()]
            print(f"\nActive threads: {len(active_threads)}")
            for t in active_threads:
                print(f"  - {t.name} ({'daemon' if t.daemon else 'main'})")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nStopping lock monitor...")
        print_thread_stacks()

if __name__ == "__main__":
    print("Lock debugging utilities loaded.")
    print("Usage:")
    print("  print_thread_stacks() - Print all thread stack traces")
    print("  monitor_locks(beacon_cache) - Monitor lock status continuously")