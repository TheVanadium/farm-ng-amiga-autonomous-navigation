import { Box, Button, Grid2, IconButton, List, ListItem, ListItemButton, ListItemText, Pagination, TextField, Typography } from "@mui/material";
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import CheckIcon from '@mui/icons-material/Check';
import React, { useState, useRef } from "react";
import { TrackType } from "./TrackCreateMenu";
import { useKeyboard } from "../context/KeyboardContext";

interface TrackSelectProps {
    selectedTrack: string,
    selectTrack: (tName: string) => void,
    tracks: Array<string>,
    lines: Array<string>,
    editTracks: (newTracks: Array<string>) => void,
    editLines: (newLines: Array<string>) => void,
    selectType: (type: TrackType) => void,
    selectedType: TrackType
};


export default function TrackSelectMenu(props: TrackSelectProps) {
    const [editingTrack, setEditingTrack] = useState<string | null>(null);
    const [editedName, setEditedName] = useState<string>("");
    const [duplicateNameError, setDuplicateNameError] = useState("");
    const [pageNumber, setPageNumber] = useState(1);
    const [displayedType, setDisplayedType] = useState(props.selectedType);
    const inputRef = useRef<HTMLInputElement>(null);

    // Keyboard
    const { openKeyboard } = useKeyboard();

    function removeTrack(tName: string): void {
        let delete_url: string;
        if (displayedType === TrackType.standard) {
            delete_url = `${import.meta.env.VITE_API_URL}/delete_track/${tName}`;
        } else {
            delete_url = `${import.meta.env.VITE_API_URL}/line/delete/${tName}`;
        }
        fetch(delete_url, { method: "POST" })
            .then(response => response.json())
            .then(_data => {
                if (displayedType === TrackType.standard) {
                    props.editTracks(props.tracks.filter(track => track !== tName));
                    if (tName === props.selectedTrack) {
                        props.selectTrack("");
                    }
                } else {
                    props.editLines(props.lines.filter(line => line !== tName));
                    if (tName === props.selectedTrack) {
                        props.selectTrack("");
                    }
                }
        });
    }

    function startEditing(tName: string): void {
        setEditingTrack(tName);
        setEditedName(tName);
        setDuplicateNameError("");
    }

    function saveTrackName(oldName: string): void {
        const trimmedName = editedName.trim();
        let tracksArray;
        if (displayedType === TrackType.standard) {
            tracksArray = props.tracks;
        } else {
            tracksArray = props.lines;
        }
        if (!trimmedName || (trimmedName !== oldName && tracksArray.includes(trimmedName))) {
            setDuplicateNameError(trimmedName);
            setEditedName(oldName);
            return;
        }

        const newTrackNames = tracksArray.map(t => t === oldName ? trimmedName : t);

        let editURL;
        if (displayedType === TrackType.standard) {
            editURL = `${import.meta.env.VITE_API_URL}/edit_track`
        } else {
            editURL = `${import.meta.env.VITE_API_URL}/line/edit`
        }
        fetch(editURL, {
            method: "POST",
            body: JSON.stringify({
                current_name: oldName,
                new_name: trimmedName
            }),
            headers: {
                "Content-Type": "application/json"
            }
        })
            .then(response => {
                if (!response.ok) throw new Error(`Failed to rename track: ${response.statusText}`);
                return response.json();
            })
            .then(_data => {
                if (displayedType === TrackType.standard) {
                    props.editTracks(newTrackNames);
                } else {
                    props.editLines(newTrackNames);
                }
                if (displayedType === props.selectedType && props.selectedTrack === oldName) {
                    props.selectTrack(trimmedName);
                }
                setEditingTrack(null);
                setDuplicateNameError("");
            });
    }

    const iconStyle = { fontSize: 45 };
    const boxStyle = { bgcolor: "#cce7eb", p: 4, margin: "20px 0 0 0", boxShadow: 24 };

    let buttonStyle = { 
        fontSize: "20px", 
        whiteSpace: "nowrap", 
        minWidth: "120px", 
        height:"40px" 
    };

    function getTrackTypeText() {
        switch(displayedType) {
            case TrackType.standard:
                return "Standard";
            case TrackType.line:
                return "Line";
        }
    }

    function changeTrackType() {
        switch(displayedType) {
            case TrackType.standard:
                setDisplayedType(TrackType.line);
                break;
            case TrackType.line:
                setDisplayedType(TrackType.standard);
                break;
        }
    }
    const maxDisplayedTracks = 6;
    function numberOfPages() {
        if(displayedType === TrackType.standard) {
            return Math.ceil(props.tracks.length / maxDisplayedTracks);
        } else {
            return Math.ceil(props.lines.length / maxDisplayedTracks);
        }
    }
    function getCurrentTrackList() {
        let toDisplay: Array<string>;
        
        switch (displayedType) {
            case TrackType.standard:
                toDisplay = props.tracks;
                break;
            case TrackType.line:
                toDisplay = props.lines;
                break;
        }
        let startInd = maxDisplayedTracks * (pageNumber - 1);
        let endInd = Math.min(toDisplay.length, startInd + maxDisplayedTracks);
        toDisplay = toDisplay.slice(startInd, endInd);

        return toDisplay.map(tName => (
            <ListItem
                key={tName}
                secondaryAction={
                    <>
                        {editingTrack === tName ? (
                            <IconButton onClick={() => saveTrackName(tName)}>
                                <CheckIcon sx={iconStyle} />
                            </IconButton>
                        ) : (
                            <IconButton onClick={() => startEditing(tName)}>
                                <EditIcon sx={iconStyle} />
                            </IconButton>
                        )}
                        <IconButton onClick={() => removeTrack(tName)}>
                            <DeleteIcon sx={iconStyle} />
                        </IconButton>
                    </>
                }
                disablePadding
            >
                {editingTrack === tName ? (
                    <TextField
                        inputRef={inputRef}
                        value={editedName}
                        onChange={(e) => {
                            setEditedName(e.target.value);
                            setDuplicateNameError("");
                        }}
                        onKeyDown={(e) => e.key === "Enter" && saveTrackName(tName)}
                        onFocus={() => openKeyboard(setEditedName, editedName, inputRef)}
                        //onBlur={() => saveTrackName(tName)}
                        error={duplicateNameError !== ""}
                        helperText={duplicateNameError ? `Track name: ${duplicateNameError} already exists.` : ""}
                        autoFocus
                        fullWidth
                    />
                ) : (
                    <ListItemButton onClick={() => {
                        props.selectTrack(tName);
                        props.selectType(displayedType);
                    }}>
                        <ListItemText primary={tName} />
                    </ListItemButton>
                )}
            </ListItem>
        ));
    }

    function handlePageChange(event: React.ChangeEvent<unknown>, value: number) {
        setPageNumber(value);
    }

    return (
        <Box sx={boxStyle}>
            <Grid2 container direction="row" spacing={2} sx={{justifyContent: "center", alignItems: "center"}}>
                {/*<Grid2 size="grow"></Grid2>*/}
                <Grid2 size="auto">
                    <Typography variant="h5">Available</Typography>
                </Grid2>
                <Grid2 size="auto">
                    <Button variant="contained" style={buttonStyle} onClick={changeTrackType}>{getTrackTypeText()}</Button>
                </Grid2>
                <Grid2 size="auto">
                    <Typography variant="h5">Tracks:</Typography>
                </Grid2>
            <Grid2 size={12}>
            <List>
                {getCurrentTrackList()}
            </List>
            </Grid2>
            <Grid2 size={12} sx={{justifyContent: "center", alignItems: "center", display: "flex"}}>
            
            <Pagination count={numberOfPages()} page={pageNumber} onChange={handlePageChange} color="primary" size="large" />
            
            </Grid2>
            </Grid2>
        </Box>
    );
}
