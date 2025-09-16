import { Box } from "@mui/material";

// 0 = left camera
// 1 = center camera
// 2 = right camera

interface CameraFeedProps {
    orientation: string;
}

function orientationToIp(orientation: string) {
    let baseIp = "http://127.0.0.1";
    switch (orientation) {
        case "left":
            baseIp += ":5011/rgb";
            break;
        case "center":
            baseIp += ":5012/rgb";
            break;
        case "right":
            baseIp += ":5013/rgb";
            break;
        default:
            baseIp += ":5012/rgb";
    }
    return baseIp;
}

export default function CameraFeed(props: CameraFeedProps) {
    return (
        <Box style={{ backgroundColor: "#000", height: "400px", width: "640px", color: "white", }} >
            <img
                src={orientationToIp(props.orientation)}
                width="640"
                height="400"
            />
        </Box>
    );
}
