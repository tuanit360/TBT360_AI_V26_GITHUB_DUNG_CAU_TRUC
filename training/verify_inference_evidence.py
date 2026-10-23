"""Independently audit saved SD1.5 inference evidence without loading a model.

A PASS verifies image/report integrity and the basic image gate only.
It never certifies that inference actually ran, nor architectural accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from app.generated_image_gate import validate_generated_image

EXPECTED_STATUS = 'DIFFUSERS_INFERENCE_EXECUTED_NOT_QUALITY_VERIFIED'


def verify_inference_evidence(report: Path, image: Path) -> dict:
    report, image = Path(report), Path(image)
    try:
        record = json.loads(report.read_text(encoding='utf-8'))
        if not isinstance(record, dict) or record.get('status') != EXPECTED_STATUS:
            raise ValueError('Report is not a successful inference declaration')
        if record.get('quality_evaluated') is not False:
            raise ValueError('Report must not claim architecture quality verification')
        if not isinstance(record.get('image_sha256'), str):
            raise ValueError('Missing image checksum')
        if not isinstance(record.get('adapter_sha256'), str):
            raise ValueError('Missing adapter checksum')
        if Path(record.get('image', '')).resolve() != image.resolve():
            raise ValueError('Image path differs from the saved report')
        with image.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != record['image_sha256']:
            raise ValueError('Generated PNG checksum mismatch')
        with Image.open(image) as decoded:
            if decoded.format != 'PNG':
                raise ValueError('Evidence must contain a real PNG image')
            decoded.verify()
        with Image.open(image) as decoded:
            evidence = validate_generated_image(decoded, expected_size=(512, 512))
        if evidence != record.get('basic_image_gate'):
            raise ValueError('Recorded image gate metrics differ from actual image')
        mode = record.get('generation_mode')
        if mode not in ('text2img', 'img2img'):
            raise ValueError('Missing or invalid generation mode')
        if mode == 'img2img':
            source_name = record.get('reference_image')
            if not isinstance(source_name, str) or not source_name:
                raise ValueError('Missing image-to-image reference')
            source = Path(source_name)
            if not 0 < record.get('strength', 0) <= 1:
                raise ValueError('Invalid image-to-image strength')
            if not isinstance(record.get('steps'), int) or int(record['steps'] * record['strength']) < 1:
                raise ValueError('Image-to-image evidence has zero effective denoising steps')
            with source.open('rb') as stream:
                source_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if source_digest != record.get('reference_sha256'):
                raise ValueError('Reference image checksum mismatch')
            with Image.open(source) as reference_image:
                if reference_image.width < 128 or reference_image.height < 128:
                    raise ValueError('Reference image is too small')
                reference_image.verify()
            if record.get('reference_geometry_verified') is not False:
                raise ValueError('Geometry verification cannot be inferred from image integrity')
        elif record.get('reference_image') is not None or record.get('reference_sha256') is not None:
            raise ValueError('Text-to-image evidence contains unexpected reference')
        return {
            'status': 'ARTIFACT_INTEGRITY_PASS_NOT_MODEL_PROVEN',
            'image_sha256': digest,
            'architecture_quality_verified': False,
            'real_model_execution_proven_by_artifacts_alone': False,
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return {'status': 'BLOCKED', 'reason': f'{type(exc).__name__}: {exc}'[:300]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--image', required=True, type=Path)
    args = parser.parse_args()
    result = verify_inference_evidence(args.report, args.image)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result['status'] != 'ARTIFACT_INTEGRITY_PASS_NOT_MODEL_PROVEN':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
