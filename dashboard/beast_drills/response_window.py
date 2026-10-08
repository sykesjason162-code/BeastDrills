MIN_FRAMES = 20

def compute_response_window_frames(drill: dict, default_frames: int = 0) -> int:

    manual = drill.get("response_window_frames")
    if manual is not None:
        return manual
    return default_frames if default_frames and default_frames > 0 else MIN_FRAMES
