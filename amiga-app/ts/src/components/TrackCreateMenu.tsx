import { Typography, TextField, Button, Grid2, Box } from "@mui/material";
import { useState, useRef } from "react";
import "react-simple-keyboard/build/css/index.css";
import { useKeyboard } from "../context/KeyboardContext";

export enum TrackType {
    line,
    standard
};

interface TrackCreateProps {
    selectTrack: (trackName: string) => void,
    tracks: Array<string>,
    trackBeingCreated: boolean,
    setTrackBeingCreated: (setting: boolean) => void
};

export default function TrackCreateMenu(props: TrackCreateProps) {
    const [newTrackName, setNewTrackName] = useState("");
    const [trackType, setTrackType] = useState(TrackType.standard);
    // This variable will store the error message associated with creating a given track
    const [trackCreationError, setTrackCreationError] = useState("");
    const [calibratingTurn, setCalibratingTurn] = useState(false);
    const [lineCreated, setLineCreated] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    // Keyboard
    const { openKeyboard } = useKeyboard();
    
    /*
    The add new track button should not add tracks directly into local storage;
    We have to make a call to backend API for the farmer to guide robot and create it, then it is added to backend and fetched
    */

    function createTrack() {
	    const trimmed = newTrackName.trim();
	    
	    if (trimmed === "") {
		    setTrackCreationError("Track name cannot be empty.");
		    return;
	    }
        if (trimmed.includes("\\") || trimmed.includes("/")) {
            setTrackCreationError("Track name cannot include the characters \\ or /");
            return;
        }
        console.log(props.tracks, trimmed);
	    if (props.tracks.includes(trimmed)) {
		    setTrackCreationError(`Track name: ${trimmed} already exists`);
		    return;
	    }

	    setTrackCreationError("");

	    // API call to start recording the track
        let record_url;
        if (trackType == TrackType.line) {
            record_url = `${import.meta.env.VITE_API_URL}/line/record/start/${trimmed}`;
        } else {
            record_url = `${import.meta.env.VITE_API_URL}/record/start/${trimmed}`;
        }
	    fetch(record_url, { method: "POST",})
	    .then(response => response.json())
	    .then(_data => {
            props.setTrackBeingCreated(true);
	    });
	}

    function endTrackCreation() {
        // Make an API call to stop creating track object
        let stop_url;
        if (trackType == TrackType.line) {
            stop_url = `${import.meta.env.VITE_API_URL}/line/record/stop`;
        } else {
            stop_url = `${import.meta.env.VITE_API_URL}/record/stop`;
        }
        fetch(stop_url , {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log(data.message);
            if (trackType == TrackType.standard) {
                props.setTrackBeingCreated(false);
            } else {
                setLineCreated(true);
            }
            
        });
    }

    const boxStyle = {
        bgcolor: "#cce7eb",
        p: 4,
        margin: "20px 0 0 0",
        boxShadow: 24,
    };

    function getTrackTypeButtonText() {
        switch (trackType) {
            case TrackType.line: {
                return "Line";
            }
            case TrackType.standard: {
                return "Standard";
            }      
        }
    }

    function swapTrackType() {
        switch(trackType) {
            case TrackType.line: {
                setTrackType(TrackType.standard);
                return;
            }
            case TrackType.standard: {
                setTrackType(TrackType.line);
                return;
            }
        }
    }

    let buttonStyle = { 
        fontSize: "17px", 
        whiteSpace: "nowrap", 
        width: "200px", 
        height:"50px" 
    };

    function lineTrackButtons() {
        function calibrateTurn() {
            const START_URL = `${import.meta.env.VITE_API_URL}/line/calibrate_turn/start`;
            fetch(START_URL , {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            })
            .then(response => response.json())
            .then(data => {
                setCalibratingTurn(true);
            });
        }
        function addTurnSegment() {
            const SEGMENT_URL = `${import.meta.env.VITE_API_URL}/line/calibrate_turn/segment`;
            fetch(SEGMENT_URL , {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            });
        }
        function endCalibration() {
            const END_URL = `${import.meta.env.VITE_API_URL}/line/calibrate_turn/end`;
            fetch(END_URL , {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            })
            .then(response => response.json())
            .then(data => {
                setCalibratingTurn(false);
                props.setTrackBeingCreated(false);
                setLineCreated(false);
            });
        }

        function getLeftButton() {
            return !calibratingTurn ?
            <Button variant="contained" style={buttonStyle} disabled={!lineCreated} onClick={calibrateTurn}> Calibrate Turn </Button> :
            <Button variant="contained" style={buttonStyle} onClick={addTurnSegment}> Add Turn Segment </Button>
        }
        return (<>
        <Grid2 size={6}>
            {getLeftButton()}
        </Grid2>
        <Grid2 size={6}>
            <Button variant="contained" style={buttonStyle} onClick={endCalibration} disabled={!lineCreated}> End Calibration </Button>
        </Grid2>
        </>);
    }

    
    return (
        <>
        <Box sx={boxStyle}>
            <Grid2 container rowSpacing={2} spacing={3} style={{display: "flex", alignItems: "center"}}>
                <Grid2 size={4}>
                    <Typography variant="h5">
                        Track Type:
                    </Typography>
                </Grid2>
                <Grid2 size={8}>
                    <Button variant="contained" onClick={swapTrackType} style={buttonStyle}>
                        { getTrackTypeButtonText() }
                    </Button>
                </Grid2>
                <Grid2 size={4}>
                    <Typography variant="h5">
                        Track Name:
                    </Typography>
                </Grid2>
                <Grid2 size={8}>
                    <TextField
                        inputRef={inputRef}
                        value={newTrackName}
                        onChange={(e) => setNewTrackName(e.target.value)}
                        onFocus={() => openKeyboard(setNewTrackName, newTrackName, inputRef)}
                        placeholder="Name of your track"
                        disabled={props.trackBeingCreated}
                        error={trackCreationError !== ""}
                        helperText={trackCreationError}
                        style={{ width: "250px"}}
                    />         
                </Grid2>
                <Grid2 size={6}>
                    <Button variant="contained" disabled={props.trackBeingCreated} onClick={createTrack} style={buttonStyle}>
                        Create Track
                    </Button>
                </Grid2>
                <Grid2 size={6}>
                    <Button variant="contained" disabled={!props.trackBeingCreated || lineCreated} onClick={endTrackCreation} style={buttonStyle}>
                        End Track
                    </Button>
                </Grid2>
                { (trackType === TrackType.line) ? lineTrackButtons() : <></>}
            </Grid2>
        </Box>
        </>
    );
}

