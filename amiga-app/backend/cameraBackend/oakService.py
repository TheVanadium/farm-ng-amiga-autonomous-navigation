# Modified code from
# https://github.com/luxonis/depthai-experiments/blob/master/gen2-poe-tcp-streaming/oak.py
# https://docs.luxonis.com/software/depthai/examples/script_mjpeg_server/

import depthai as dai
import time


# Upload configs and pipeline to the cameras
## camera_ip: ip of the camera to upload to
def uploadService(cameraIp, cameraPort):
    FPS = 5
    pipeline = dai.Pipeline()

    # RGB node
    ## Source node
    RGB_SOCKET = dai.CameraBoardSocket.CAM_C
    camRgb = pipeline.create(dai.node.ColorCamera)
    camRgb.setBoardSocket(RGB_SOCKET)
    camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_800_P)
    camRgb.setFps(FPS)
    camRgb.setIspScale(1, 2)
    camRgb.setVideoSize(640, 400)

    # Video encoder node
    ## Link rgb output to video encoder input
    videoEnc = pipeline.create(dai.node.VideoEncoder)
    camRgb.video.link(videoEnc.input)

    videoEnc.setDefaultProfilePreset(FPS, dai.VideoEncoderProperties.Profile.MJPEG)

    # Streaming server node
    ## Link video encoder output to streaming server input
    server = pipeline.create(dai.node.Script)
    videoEnc.bitstream.link(server.inputs["frame"])

    server.setProcessor(dai.ProcessorType.LEON_CSS)
    server.inputs["frame"].setBlocking(False)
    server.inputs["frame"].setQueueSize(1)

    # server.setScript(f"""
    # import socket
    # import time
    #
    # server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # server.bind(("0.0.0.0", {cameraPort}))
    # server.listen()
    # node.warn("Server up")
    #
    # while True:
    #     conn, client = server.accept()
    #     node.warn(f"Connected to client IP: {{client}}")
    #     try:
    #         while True:
    #             pck = node.io["frame"].get()
    #             data = pck.getData()
    #             ts = pck.getTimestamp()
    #             header = f"ABCDE " + str(ts.total_seconds()).ljust(18) + str(len(data)).ljust(8)
    #             # node.warn(f'>{{header}}<')
    #             conn.send(bytes(header, encoding='ascii'))
    #             conn.send(data)
    #
    #     except Exception as e:
    #         node.warn("Client disconnected")
    # """)

    server.setScript(
        f"""
    import time
    import socket
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class HTTPHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/rgb':
                try:
                    delay = {1/FPS}
                    self.send_response(200)
                    self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
                    self.end_headers()
                    while True:
                        frame = node.io['frame'].get()

                        self.wfile.write("--jpgboundary".encode())
                        self.wfile.write(bytes([13, 10]))
                        self.send_header('Content-type', 'image/jpeg')
                        self.send_header('Content-length', str(len(frame.getData())))
                        self.end_headers()
                        self.wfile.write(frame.getData())
                        self.end_headers()
                        time.sleep(delay)

                except Exception as ex:
                    node.warn("Client disconnected")

    class ThreadingSimpleServer(HTTPServer):
        pass

    with ThreadingSimpleServer(("", {cameraPort}), HTTPHandler) as httpd:
        node.warn(f"Serving RGB MJPEG stream at {cameraIp + ":" + cameraPort + "/rgb"}")
        httpd.serve_forever()
    """
    )

    device_info = dai.DeviceInfo(cameraIp)

    with dai.Device(pipeline, device_info) as device:
        print("Connected to " + cameraIp)
        while True:
            time.sleep(1)
