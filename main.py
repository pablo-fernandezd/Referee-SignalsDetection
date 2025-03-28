import os
import cv2
import torch
from datetime import datetime
from ultralytics import YOLO

# GPU Configuration
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
MODEL_SIZE = 640  # Model input size (must be multiple of 32)
SEGMENT_DURATION = 3600  # 1 hour in seconds
CONFIDENCE_THRESHOLD = 0.7


class RefereeProcessor:
    def __init__(self):
        # Load trained model and move to target device
        self.model = YOLO('referee17february.pt').to(DEVICE)
        self.model.fuse()

        # CUDA optimizations
        if DEVICE == 'cuda':
            self.model.half()  # Use FP16 precision
            torch.backends.cudnn.benchmark = True

        # Get referee class ID from model metadata
        self.class_id = self._get_referee_class_id()

    def _get_referee_class_id(self):
        """Retrieves the class ID for 'referee' from model names"""
        if 'referee' in self.model.names.values():
            return [k for k, v in self.model.names.items() if v == 'referee'][0]
        return 0  # Default to first class if not found

    def process_videos(self, input_dir='dataVideo', output_dir='forLabel', used_dir='used'):
        """Main processing pipeline for video files"""
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(used_dir, exist_ok=True)

        for video_file in self._get_video_files(input_dir):
            video_path = os.path.join(input_dir, video_file)
            self._process_single_video(video_path, output_dir, used_dir)

    def _get_video_files(self, directory):
        """Get list of .mp4 files in target directory"""
        return [f for f in os.listdir(directory) if f.endswith('.mp4')]

    def _process_single_video(self, video_path, output_dir, used_dir):
        """Process individual video file"""
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        # Video segmentation setup
        frames_per_segment = SEGMENT_DURATION * fps
        segment_counter = 1
        current_frame = 0
        video_writer = None
        last_valid_frame = None

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Process frame through detection pipeline
                processed_frame = self._process_frame(frame, last_valid_frame)

                if processed_frame is not None:
                    last_valid_frame = processed_frame
                    current_frame += 1

                    # Manage video segmentation
                    if current_frame % frames_per_segment == 0:
                        self._close_writer(video_writer)
                        video_writer = self._create_new_writer(video_path, output_dir, segment_counter, fps)
                        segment_counter += 1

                    # Initialize writer if needed
                    if video_writer is None:
                        video_writer = self._create_new_writer(video_path, output_dir, segment_counter, fps)

                    # Write processed frame
                    video_writer.write(processed_frame)

        finally:
            # Cleanup resources
            self._close_writer(video_writer)
            cap.release()
            self._move_processed_file(video_path, used_dir)

    def _process_frame(self, frame, last_valid):
        """Full frame processing pipeline"""
        # Prepare tensor for model input
        frame_tensor = self._prepare_frame_tensor(frame)

        # Run model inference
        results = self.model.track(
            frame_tensor,
            conf=CONFIDENCE_THRESHOLD,
            classes=[self.class_id],
            verbose=False
        )[0]

        # Handle detection and cropping
        return self._handle_frame_cropping(frame, results, last_valid)

    def _prepare_frame_tensor(self, frame):
        """Convert frame to optimized tensor format"""
        # Convert to RGB and move to GPU
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb_frame).to(DEVICE)

        # Apply device-specific optimizations
        if DEVICE == 'cuda':
            tensor = tensor.half()  # FP16 for faster computation
        else:
            tensor = tensor.float()

        # Normalize and reshape tensor
        tensor = tensor.permute(2, 0, 1) / 255.0  # HWC to CHW
        return tensor.unsqueeze(0)  # Add batch dimension

    def _handle_frame_cropping(self, frame, results, last_valid):
        """Handle referee detection and image cropping"""
        if results.boxes.xyxy.shape[0] > 0:
            # Extract bounding box coordinates
            x1, y1, x2, y2 = map(int, results.boxes.xyxy[0].cpu().numpy())

            # Calculate aspect-preserving dimensions
            height, width = y2 - y1, x2 - x1
            aspect_ratio = width / height
            target_height = MODEL_SIZE
            target_width = int(target_height * aspect_ratio)

            # Crop and resize
            cropped = frame[y1:y2, x1:x2]
            return cv2.resize(cropped, (target_width, target_height))

        return last_valid  # Return previous valid frame if no detection

    def _create_new_writer(self, video_path, output_dir, segment_num, fps):
        """Initialize new video writer for segment"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(
            output_dir,
            f"{base_name}_{timestamp}_part{segment_num}.mp4"
        )
        return cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            fps,
            (MODEL_SIZE, MODEL_SIZE)
        )

    def _close_writer(self, writer):
        """Safely close video writer"""
        if writer is not None:
            writer.release()

    def _move_processed_file(self, src_path, dest_dir):
        """Move processed file to completed directory"""
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, os.path.basename(src_path))
        os.rename(src_path, dest_path)


if __name__ == "__main__":
    processor = RefereeProcessor()
    processor.process_videos()
