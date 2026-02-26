# Contract: MJPEG Video Stream (HTTP)

**Endpoint**: `http://<videoStreamHost>:<videoStreamPort>/video_feed`  
**Default**: `http://<brokerHost>:5000/video_feed`  
**Direction**: Mobile App → Backend (Jetson Flask server)  
**Protocol**: HTTP/1.1 — multipart/x-mixed-replace  
**Authentication**: HTTP Basic Auth (username/password stored separately from MQTT credentials)  
**Network scope**: Local farm network (LAN/intranet) only — stream not exposed to internet  
**Access pattern**: On-demand only; never auto-fetched (FR-017)

---

## HTTP Request

```
GET /video_feed HTTP/1.1
Host: <videoStreamHost>:<videoStreamPort>
Authorization: Basic <base64(username:password)>
Accept: multipart/x-mixed-replace
```

## HTTP Response

```
HTTP/1.1 200 OK
Content-Type: multipart/x-mixed-replace; boundary=frame

--frame
Content-Type: image/jpeg

<JPEG binary data>
--frame
Content-Type: image/jpeg

<JPEG binary data>
...
```

## Mobile-Side Behaviour

- Stream opened only after explicit user tap of "View Feed" action
- `MjpegViewer` widget opens a `StreamedResponse` via Dart `http.Client`, reads chunked body, parses JPEG boundaries, renders via `Image.memory`
- Stream connection closed on modal/overlay dismiss (`dispose()`)
- On connection failure (timeout, 401, 403, unreachable): displays inline error message: `"Stream unavailable — ensure you are on the local farm network"`
- HTTP 401 Unauthorized: prompts user to check video stream credentials in settings

## Error States

| HTTP Status / Condition | Mobile Behaviour |
|---|---|
| 200 OK | Stream frames render normally |
| 401 Unauthorized | "Authentication failed — check video credentials in Settings" |
| Connection refused / timeout | "Stream unavailable — ensure you are on the local farm network" |
| Slow / stalled frames | Spinner overlay after 5 s with "Waiting for stream…" |
