
import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"CWD: {os.getcwd()}")

try:
    import youtube_transcript_api
    print(f"\nModule: youtube_transcript_api")
    print(f"Location: {os.path.dirname(youtube_transcript_api.__file__)}")
    print(f"Version: {getattr(youtube_transcript_api, '__version__', 'Unknown')}")
except Exception as e:
    print(f"Error importing module: {e}")

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    print(f"\nClass: YouTubeTranscriptApi")
    print(f"Dir: {dir(YouTubeTranscriptApi)}")
    
    if hasattr(YouTubeTranscriptApi, 'get_transcript'):
        print("SUCCESS: get_transcript found.")
    else:
        print("FAILURE: get_transcript NOT found.")
        
except Exception as e:
    print(f"Error importing class: {e}")
