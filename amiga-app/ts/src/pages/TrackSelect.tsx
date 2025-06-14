import { Button, Collapse, Container, Grid2, LinearProgress, Stack, Tab, Tabs, Typography } from "@mui/material";
import BackButton from "../components/BackButton";
import CameraFeed from "../components/CameraFeed";
import React, { SyntheticEvent, useEffect, useState } from "react";
import TrackSelectMenu from "../components/TrackSelectMenu";
import TrackCreateMenu, {TrackType} from "../components/TrackCreateMenu";
import { JsonView } from "react-json-view-lite";
import TrackRunMenu from "../components/TrackRunMenu";

export default function TrackSelect() {
    const [tabValue, setTabValue] = useState(1);
    const [currentCamera, setCurrentCamera] = useState("center");
    const [selectedTrack, setSelectedTrack] = useState("");
    const [selectedButton, setSelectedButton] = useState("select");
    const [existingTracks, setExistingTracks] = useState([""]);
    const [existingLines, setExistingLines] = useState([""]);
    const [tracksUpdate, setTracksUpdate] = useState(true);
    const [selectedType, setSelectedType] = useState(TrackType.standard);

    const selectTrack = (tName: string) => setSelectedTrack(tName);
    const editTracks = (newTracks: Array<string>) => setExistingTracks(newTracks);
    const editLines = (newLines: Array<string>) => setExistingLines(newLines);
    const forceTracksUpdate = () => setTracksUpdate(true);
    const selectType = (type: TrackType) => setSelectedType(type);

    // Whether or not the track creation page is currently creating a track
    // If we are currently creating a track, and the user swaps to a different menu
    // We must send a request to the backend to end track creation
    const [trackBeingCreated, setTrackBeingCreated] = useState(false);
    const changeTrackBeingCreated = (flag: boolean) => setTrackBeingCreated(flag);
    function selectButton(newButton: string): void {
        if (selectedButton === "add") {
            forceTracksUpdate();
            if (trackBeingCreated) {
                // Make an API call to stop creating track object
                const STOP_TRACK = `${import.meta.env.VITE_API_URL}/stop_recording`;
                const STOP_LINE = `${import.meta.env.VITE_API_URL}/line/end_creation`;
                fetch(STOP_TRACK , {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    }
                })
                .then((response) => response.json())
                .then(data => {
                    console.log(data.message);
                    setTrackBeingCreated(false);
                });
                fetch(STOP_LINE, {method: "POST"});
            }
        } else if (selectedButton === "run") {
            const STOP_RUN = `${import.meta.env.VITE_API_URL}/follow/stop`;
            fetch(STOP_RUN, {method: "POST"});
        }
        setSelectedButton(newButton);
    }

    function fetchTracks() {
        if (!tracksUpdate) {return;}
        const trackListEndpoint = `${import.meta.env.VITE_API_URL}/list_tracks`;
        const lineListEndpoint = `${import.meta.env.VITE_API_URL}/line/list`;
        
        fetch(trackListEndpoint, { method: "GET" })
        .then((response) => response.json())
        .then((result) => {
            const trackArr = result["tracks"];
            setExistingTracks(trackArr);
        });
        fetch(lineListEndpoint, {method: "GET"})
        .then((response) => response.json())
        .then((result) => {
            const lineArr = result["lines"];
            setExistingLines(lineArr);
        });
        setTracksUpdate(false);
    }
    useEffect(fetchTracks, [tracksUpdate]);

    function getMenuComponent() {
        switch(selectedButton) {
            case "add":
                return <TrackCreateMenu trackBeingCreated={trackBeingCreated} setTrackBeingCreated={changeTrackBeingCreated} selectTrack={selectTrack} tracks={existingTracks}/>;
            case "select":
                return (
                    <TrackSelectMenu 
                        selectedTrack={selectedTrack} 
                        selectTrack={selectTrack}
                        selectType={selectType}
                        tracks={existingTracks} 
                        lines={existingLines}
                        editTracks={editTracks}
                        editLines={editLines}
                        selectedType={selectedType}
                    />
                );
            case "run":
                return (<TrackRunMenu selectedType={selectedType} selectedTrack={selectedTrack}></TrackRunMenu>);
            default:
                return (<></>);
        }
    }
    

    const handleCameraTabChange = (event: SyntheticEvent, newValue: number) => {
        setTabValue(newValue);
        setCurrentCamera(event.currentTarget.id);
    };

    const testPointCloud = () => {
        const align = `${import.meta.env.VITE_API_URL}/pointcloud/align`;
        fetch(align, { method: "GET" })
        .then((response) => console.log(response.json()))
        .catch((err) => console.log(err));

    const save = `${import.meta.env.VITE_API_URL}/pointcloud/save`;
        fetch(save, { method: "GET" })
        .then((response) => console.log(response.json()))
        .catch((err) => console.log(err));
    }

    const buttonStyle = {
        width: "150px",
        height: "130px",
        borderRadius: "4px"
    };

    return (
        <>
            <Grid2 container rowSpacing={2} style={{ margin: "30px 30px 0 30px" }} >
                <Grid2 size={1} display="flex" justifyContent="center" alignItems="center">
                    <BackButton />
                </Grid2>
                <Grid2 size={10} display="flex" justifyContent="center" alignItems="center">
                    <Typography variant="h2">Track Select</Typography>
                </Grid2>
                <Grid2 size="grow" />

                <Grid2 size={6}>
                    <div style={{ width: "640px" }}>
                        <Tabs value={tabValue} onChange={handleCameraTabChange} variant="fullWidth">
                            <Tab label={<Typography>Left Camera</Typography>} id="left" />
                            <Tab label={<Typography>Center Camera</Typography>} id="center" />
                            <Tab label={<Typography>Right Camera</Typography>} id="right" />
                        </Tabs>
                    </div> 
                    <CameraFeed orientation={currentCamera} />
                    <Typography variant="h5">
                            Current Track: {
                                selectedTrack === "" ? "None" : selectedTrack
                            }
                        </Typography>
                    </Grid2>

                <Grid2 size={.6} />

                <Grid2 size={5.4}>
                        <Container style={{display:"flex", justifyContent:"space-between", padding:"0px"}}>
                            <Button variant="contained" style={buttonStyle} onClick={() => selectButton("add")} color={selectedButton==="add" ? "secondary" : "primary"}>
                                <Typography variant="h5">Add New Track</Typography>
                            </Button>
                            <Button variant="contained" style={buttonStyle} onClick={() => selectButton("select")} color={selectedButton==="select" ? "secondary" : "primary"}>
                                <Typography variant="h5" >Select Track</Typography>
                            </Button>
                            <Button variant="contained" disabled={selectedTrack===""} style={buttonStyle} onClick={() => selectButton("run")} color={selectedButton==="run" ? "secondary" : "primary"}>
                                <Typography variant="h5">Run Track</Typography>
                            </Button>

                        </Container>

                        {getMenuComponent()}
                        
                </Grid2>

                <Grid2 size="grow" />
                <Grid2 size={0} />

                <Grid2 size={4}/>
                

            {/*<Button variant="contained" style={buttonStyle} onClick={() => testPointCloud()}>
                test
            </Button>*/}
            </Grid2>
        </>
    );
}