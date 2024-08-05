import subprocess

def check_firefox():
    try:
        result = subprocess.run(['firefox', '--version'], stdout=subprocess.PIPE)
        print(f"Firefox version: {result.stdout.decode().strip()}")
    except Exception as e:
        print(f"Failed to get Firefox version: {e}")

def check_geckodriver():
    try:
        result = subprocess.run(['geckodriver', '--version'], stdout=subprocess.PIPE)
        print(f"Geckodriver version: {result.stdout.decode().strip()}")
    except Exception as e:
        print(f"Failed to get Geckodriver version: {e}")

if __name__ == "__main__":
    check_firefox()
    check_geckodriver()
