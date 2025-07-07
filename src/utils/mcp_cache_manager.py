import subprocess
import time
import sys
import hashlib
import random
from pathlib import Path

class CacheAvailabilityManager:
    """
    Hybrid approach combining cache detection with smart fallbacks.
    This gives you the best of both worlds: intelligent detection + reliable fallback.
    """
    
    def __init__(self, script_path=None):
        self.script_name = Path(script_path or sys.argv[0]).stem
        self.start_time = time.time()
    
    def log(self, message):
        """Log with timestamp and script name."""
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:5.1f}s] [{self.script_name}] {message}", file=sys.stderr)
    
    def test_uv_responsiveness(self, timeout=3):
        """Test if UV is responsive and cache is accessible."""
        try:
            # Test 1: Basic UV responsiveness
            result = subprocess.run(
                ['uv', '--version'],
                capture_output=True,
                timeout=timeout,
                text=True
            )
            if result.returncode != 0:
                return False, "UV not responsive"
            
            # Test 2: Cache directory access
            cache_result = subprocess.run(
                ['uv', 'cache', 'dir'],
                capture_output=True,
                timeout=timeout,
                text=True
            )
            if cache_result.returncode != 0:
                return False, "Cache not accessible"
            
            # Test 3: Quick cache operation (non-destructive)
            info_result = subprocess.run(
                ['uv', 'cache', 'prune', '--dry-run'],
                capture_output=True,
                timeout=timeout,
                text=True
            )
            # This might fail on older UV versions, so we don't check return code
            
            return True, "Cache available"
            
        except subprocess.TimeoutExpired:
            return False, "UV operation timed out"
        except FileNotFoundError:
            return False, "UV not found"
        except Exception as e:
            return False, f"Unexpected error: {e}"
    
    def get_deterministic_delay(self):
        """Get a consistent delay based on script name to stagger servers."""
        hash_value = int(hashlib.md5(self.script_name.encode()).hexdigest()[:8], 16)
        return (hash_value % 30) / 10.0  # 0.0 to 2.9 seconds
    
    def wait_for_cache_with_fallback(self, max_wait=15):
        """
        Primary strategy: Wait for cache availability
        Fallback strategy: Use deterministic delay
        """
        self.log("🔍 Checking cache availability...")
        
        # Strategy 1: Try to detect cache availability
        for attempt in range(int(max_wait / 0.5)):  # Check every 0.5s
            available, reason = self.test_uv_responsiveness()
            
            if available:
                elapsed = time.time() - self.start_time
                self.log(f"✅ Cache available after {elapsed:.1f}s")
                return True
            
            if attempt % 4 == 0 and attempt > 0:  # Log every 2 seconds
                elapsed = time.time() - self.start_time
                self.log(f"⏳ Cache busy ({reason}), waiting... ({elapsed:.1f}s)")
            
            time.sleep(0.5)
        
        # Strategy 2: Fallback to deterministic delay
        self.log("⚠️  Cache detection timeout, using fallback strategy")
        fallback_delay = self.get_deterministic_delay()
        
        if fallback_delay > 0:
            self.log(f"🔄 Fallback delay: {fallback_delay:.1f}s")
            time.sleep(fallback_delay)
        
        return False
    
    def safe_startup(self):
        """Execute the complete safe startup sequence."""
        self.log("🚀 Starting smart cache-aware initialization...")
        
        # Execute cache availability strategy
        cache_detected = self.wait_for_cache_with_fallback()
        
        # Additional safety for high-concurrency scenarios
        if not cache_detected:
            # Add small random jitter to break ties in worst case
            jitter = random.uniform(0.1, 0.5)
            self.log(f"🎲 Adding final jitter: {jitter:.1f}s")
            time.sleep(jitter)
        
        self.log("✅ Initialization complete, starting MCP server")