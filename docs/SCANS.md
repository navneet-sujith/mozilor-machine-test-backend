# Scan Feature Documentation

The Scan feature allows authenticated users to submit a URL for analysis. The system fetches the page, parses it for images, and evaluates accessibility attributes (alt text).

## Endpoint

`POST /web-image-analyzer/api/v1/scans/`

**Request Body:**
```json
{
  "url": "https://example.com"
}
```

**Response (201 Created):**
```json
{
  "id": 123,
  "url": "https://example.com",
  "total_images": 10,
  "alt_images": 8,
  "non_alt_images": 2,
  "created_at": "2023-10-27T10:00:00Z"
}
```

## Scanning Rules

The scanner identifies the following as "images":
- `<img>` tags.
- `<svg>` tags (inline).
- Elements with `style="background-image: url(...)"`.

**Accessibility Criteria:**
- **Has Alt**: `alt` attribute exists and is non-empty.
- **Empty Alt**: By default, `alt=""` is considered an ACCESSIBLE image (decorative). This can be toggled via `TREAT_EMPTY_ALT_AS_PRESENT` in `app/services/scan_service.py`.
- **Missing Alt**: `alt` attribute is missing entirely.
- **Background Images**: Always counted as "missing alt" (non-accessible) unless manual review says otherwise (scanner assumes non-accessible).
- **SVGs**: Considered accessible if they have `aria-label` or `title`.

## Security & Limitations

- **SSRF Protection**: The scanner resolves hostnames and blocks private IPs (e.g., 127.0.0.1, 10.x.x.x).
- **Protocols**: Only `http` and `https` are allowed.
- **Javascript**: The scanner does NOT execute Javascript. Images loaded dynamically or lazy-loaded via JS (without `src`) might be missed or counted as broken.
- **Timeouts**: 15 seconds total timeout per scan.
- **Limits**: Max 500 images per page.

## Configuration

Settings in `app/services/scan_service.py`:
- `TREAT_EMPTY_ALT_AS_PRESENT` (bool): Default `True`.
- `MAX_IMAGE_ELEMENTS` (int): Default `500`.
- `TIMEOUT_TOTAL` (float): Default `15.0`.
