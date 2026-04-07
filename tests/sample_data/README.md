# Sample Data Directory

This directory contains test video files used for unit and integration tests.

## Structure

Test video files should be organized by format/codec for easy reference:
- MP4 files (H.264, H.265)
- MKV files
- AVI files
- ProRes files (if available)

## Usage

Test files in this directory are referenced by tests for:
- Metadata extraction (`MetadataExtractor`)
- Frame decoding (`VideoDecoder`)
- Frame-accurate seeking
- Error handling for various formats

## File Naming

Use descriptive names that indicate the video properties:
- `test_1080p_h264_30fps.mp4` - 1080p H.264 at 30fps
- `test_720p_h265_24fps.mkv` - 720p H.265 at 24fps
- etc.
