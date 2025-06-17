import { Typography, TextField, Button, Grid2, Box, Stack, Paper } from "@mui/material";
import { styled } from '@mui/material/styles';
import { useEffect, useRef, useState } from "react";
import { Vec2, FromPolar, twoDigits } from "../utils/Vec2";
import arrow from "../icons/direction-arrow.png"
import { TrackType } from "./TrackCreateMenu";
import { useKeyboard } from "../context/KeyboardContext";

interface TrackRunProps {
    selectedTrack: string,
    selectedType: TrackType
};

export default function TrackRunMenu(props: TrackRunProps) {
    const boxStyle = {
        bgcolor: "#cce7eb",
        p: 4,
        margin: "20px 0 0 0",
        boxShadow: 24,
    };

    const [currentLocation, setCurrentLocation] = useState(Vec2.Zero);
    const [startPosition, setStartPosition] = useState(Vec2.Zero);
    const [rotationAngle, updateRotationAngle] = useState(1);
    const [followingTrack, setFollowingTrack] = useState(false);
    const [trackLoaded, setTrackLoaded] = useState(false);

    const [numRows, setNumRows] = useState("1");
    const [firstTurnRight, setFirstTurnRight] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    // Keyboard
    const { openKeyboard } = useKeyboard();

    useEffect(() => {
        // go to ws:// instead of http://
        const socket_URL = `ws://${import.meta.env.VITE_API_URL.substring(7)}/filter_data`;
        const detailSocket = new WebSocket(socket_URL);

        detailSocket.onopen = (event) => {
            // console.log('Detail WebSocket connection opened:', event);
        };

        detailSocket.onmessage = (event) => {
            const transform = JSON.parse(JSON.parse(event.data))["pose"]["aFromB"];
            const translation = transform["translation"];
            setCurrentLocation(new Vec2(translation.x, translation.y));
            const zAxis = transform["rotation"]["unitQuaternion"]["imag"]["z"];
            let zAxisRotation = Math.acos(transform["rotation"]["unitQuaternion"]["real"]) * 2;
            if (zAxis < 0) {
                zAxisRotation *= -1;
            }
            updateRotationAngle(zAxisRotation);
        }

        detailSocket.onerror = (error) => {
            console.log(error);
        };

        detailSocket.onclose = (_event) => {
            // console.log('Detail WebSocket connection closed:', event);
        };
        return () => {detailSocket.close()};
    }, []);

    

    function fetchStartingPoint() {
        let trackDataEndpoint;
        if (props.selectedType === TrackType.standard) {
            trackDataEndpoint = `${import.meta.env.VITE_API_URL}/get_track/${props.selectedTrack}`;
        } else {
            trackDataEndpoint = `${import.meta.env.VITE_API_URL}/line/get_start/${props.selectedTrack}`;
        }
        fetch(trackDataEndpoint, { method: "GET" })
        .then((response) => response.json())
        .then((result) => {
            if (props.selectedType === TrackType.standard) {
                const waypoints = result["waypoints"];
                const first = waypoints[0];
                const startingPos = first["aFromB"]["translation"]
                setStartPosition(new Vec2(startingPos.x, startingPos.y));    
            } else {
                const start = result["start_position"];
                setStartPosition(new Vec2(start[0], start[1]));
            }
        });
    }

    function getDist() {
        const diff: Vec2 = currentLocation.Sub(startPosition);
        return diff.Mag();
    }

    // Returns the angle in radians between the robot's current rotation
    // and the angle it needs to rotate in order to be facing a straight line towards
    // the starting position
    function rotationTarget() {
        const diff = startPosition.Sub(currentLocation);
        const targetAngleVec = diff.Normalized();
        const currentAngleVec = FromPolar(1, rotationAngle);
        const currAngle = currentAngleVec.Argument() * 180 / Math.PI;
        const targetAngle = targetAngleVec.Argument() * 180 / Math.PI;
        // Rotate the negative of (target - curr + 90) because rotate() will go clockwise in JS
        return (-targetAngle + currAngle) - 90;
    }

    function followTrack() {
        const stateEndpoint = `${import.meta.env.VITE_API_URL}/follow/state`;

        function makeFollowTrackRequest() {
            let followTrackEndpoint;
            let requestData;
            let numRowsInt = toPosInt(numRows);
            if (numRowsInt === false) {
                return;
            }
            if (props.selectedType === TrackType.standard) {
                followTrackEndpoint = `${import.meta.env.VITE_API_URL}/follow/start/${props.selectedTrack}`;
                requestData = {method: "POST"};
            }  else {
                followTrackEndpoint = `${import.meta.env.VITE_API_URL}/line/follow/${props.selectedTrack}`;
                requestData = {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        "num_rows": numRowsInt,
                        "first_turn_right": firstTurnRight
                    })
                };
            }
            fetch(followTrackEndpoint, requestData)
            .then((response) => response.json())
            .then((result) => {
                if (!result.error) {
                    setTrackLoaded(true);
                    setFollowingTrack(true);
                } else {
                    console.error("Failed to follow track:", result.error);
                }
            });
        }

        fetch(stateEndpoint, {method: "GET"})
        .then((response) => response.json())
        .then((result) => {
            if (result.controllable) {
                makeFollowTrackRequest();
            } else {
                window.alert("Make sure the robot's filter service has converged\nAnd that the robot is set to auto mode");
            }
        });

        
        return;
    }

    function pauseTrack() {
        const pauseTrackEndpoint = `${import.meta.env.VITE_API_URL}/follow/pause`;
        fetch(pauseTrackEndpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        })
            .then((response) => response.json())
            .then((result) => {
                if (!result.error) {
                    setFollowingTrack(false);
                } else {
                    console.error("Failed to pause track:", result.error);
                }
            })
            .catch((err) => {
                console.error("Error pausing track:", err);
            });
    }

    function resumeTrack() {
        const resumeTrackEndpoint = `${import.meta.env.VITE_API_URL}/follow/resume`;
        fetch(resumeTrackEndpoint, {
            method: "POST",
        })
            .then((response) => response.json())
            .then((_result) => {
                setFollowingTrack(true);
            });
    }

    function endTrack() {
        const endTrackEndpoint = `${import.meta.env.VITE_API_URL}/follow/stop`;
        fetch(endTrackEndpoint, {method: "POST"})
        .then((response) => response.json())
        .then((_result) => {
            setFollowingTrack(false);
            setTrackLoaded(false);
        });
    }

    function rowsError() {
        let err = toPosInt(numRows) === false;
        return err;
    }

    function toPosInt(str: string) {  
        let val = +str;
        if (Number.isNaN(val)) {
            return false;
        }
        if ((val % 1) != 0) {
            return false;
        }
        if (val < 1) {
            return false;
        }
        return val;
    }

    function lineOptions() {
        if (props.selectedType != TrackType.line) {
            return;
        }
        return (<>
        <Grid2 size={6}>
            <TextField
                inputRef={inputRef}
                value={numRows}
                onChange={(event) => setNumRows(event.target.value)}
                onFocus={() => openKeyboard(
                    (input) => setNumRows(input),
                    String(numRows),
                    inputRef
                )}
                placeholder="Number of rows"
                disabled={trackLoaded}
                error={rowsError()}
                helperText={rowsError() ? "Number of rows must be a positive integer" : ""}
                style={{ width: "250px"}}
            />
        </Grid2>
        <Grid2 size={6}>
            <Button 
            style={buttonStyle} 
            variant="contained"
            onClick={
                () => {
                    setFirstTurnRight(!firstTurnRight);
                    console.log(firstTurnRight);
                }
            }>
                {firstTurnRight ? "Turning Right" : "Turning Left"}
            </Button>
        </Grid2>
        </>);
    }


    useEffect(fetchStartingPoint, [props.selectedTrack]);
    // useEffect(fetchEndingPoint, [props.selectedTrack]);

    const Item = styled(Paper)(({ theme }) => ({
        backgroundColor: '#fff',
        ...theme.typography.body2,
        padding: theme.spacing(1),
        textAlign: 'center',
        color: theme.palette.text.secondary,
        ...theme.applyStyles('dark', {
        backgroundColor: '#1A2027',
        }),
    }));

    const buttonStyle = { margin: "10px", width: "200px", height: "50px" }

    return (
    <Box sx={boxStyle}>
        <Grid2 container rowSpacing={2} columnSpacing={{ xs: 1, sm: 2, md: 3 }}>
            <Grid2 size={6}>
            <Stack spacing={2} style={{justifyContent: "center", display: "flex"}}>
                <Item>
                    <Typography variant="h6">Distance:</Typography>
                </Item>
                <Item>
                    <Typography variant="h4" style={{height: "100px"}}>{twoDigits(getDist())}<br></br>meters</Typography>
                </Item>
            </Stack>
            </Grid2>
            <Grid2 size="grow">
            <Stack spacing={2}>
                <Item><Typography variant="h6">Direction:</Typography></Item>
                <Item>
                    <img src={arrow} style={{
                        "transform": `rotate(${rotationTarget()}deg)`,
                        "width": "100px",
                        "height": "100px"
                    }}></img>
                </Item>
            </Stack>
            </Grid2>
            {lineOptions()}
            <Grid2 size={12} style={{ justifyContent: "center", display: "flex", marginTop: "20px" }}>
                <Button
                    variant="contained"
                    color="primary"
                    disabled={trackLoaded && !followingTrack}
                    onClick={!trackLoaded ? followTrack : pauseTrack}
                    style={buttonStyle}
                >
                    {!trackLoaded ? "Follow Track" : "Pause Track"}
                </Button>
                <Button
                    variant="contained"
                    color="primary"
                    disabled={!trackLoaded || (trackLoaded && followingTrack)}
                    onClick={resumeTrack}
                    style={buttonStyle}
                >
                    Resume Track
                </Button>
                <Button
                    variant="contained"
                    color="primary"
                    disabled={!trackLoaded}
                    onClick={endTrack}
                    style={buttonStyle}
                >
                    End Track
                </Button>
            </Grid2>
        </Grid2>
    </Box>
    );
}
