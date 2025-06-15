import { List, ListItemButton, ListItemText, Box, Typography } from "@mui/material";

interface TrackYieldSelectProps {
    runs: string[];
    selectedRun: string;
    onSelectRun: (runName: string) => void;
}

export default function TrackYieldSelect({ runs, selectedRun, onSelectRun }: TrackYieldSelectProps) {
    return (
        <Box>
            <Typography variant="h6" gutterBottom>
                Select Path Crop Yield
            </Typography>
            <List>
                {runs.map((runName) => (
                    <ListItemButton
                        key={runName}
                        selected={runName === selectedRun}
                        onClick={() => onSelectRun(runName)}
                    >
                        <ListItemText primary={runName} />
                    </ListItemButton>
                ))}
            </List>
        </Box>
    );
}
