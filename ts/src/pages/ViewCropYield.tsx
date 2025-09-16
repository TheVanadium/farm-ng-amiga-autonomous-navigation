// src/pages/ViewCropYield.tsx
import { Container, Grid, Typography, LinearProgress } from "@mui/material";
import BackButton from "../components/BackButton";
import TrackYieldSelect from "../components/TrackYieldSelect";
import TrackYieldInfo from "../components/TrackYieldInfo";
import { useState, useEffect } from "react";

export default function ViewCropYield() {
    const [runs, setRuns] = useState<string[]>([]);
    const [selectedRun, setSelectedRun] = useState<string>("");
    const [yieldEstimate, setYieldEstimate] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);



    //line load
    useEffect(() => {
        fetch(`${import.meta.env.VITE_API_URL}/line/list`)
            .then(res => res.json())
            .then(data => setRuns(data.lines))
            .catch(err => console.error("failed to fetch lines:", err));
    }, []);

    // Loading yield when picked
    useEffect(() => {
        if (!selectedRun) {
            setYieldEstimate(null);
            return;
        }
        setLoading(true);
        fetch(`${import.meta.env.VITE_API_URL}/get_yield/${selectedRun}`)
            .then(res => res.json())
            .then(data => setYieldEstimate(data.message))
            .catch(err => {
                console.error("failed to fetch yield:", err);
                setYieldEstimate(null);
            })
            .finally(() => setLoading(false));
    }, [selectedRun]);

    return (
        <Container sx={{ mt: 4 }}>
            <Grid container spacing={4}>
                <Grid item xs={12} display="flex" alignItems="center">
                    <BackButton />
                    <Typography variant="h4" sx={{ ml: 2 }}>
                        View Crop Yield
                    </Typography>
                </Grid>

                <Grid item xs={12} md={4}>
                    <TrackYieldSelect
                        runs={runs}             
                        selectedRun={selectedRun}
                        onSelectRun={setSelectedRun}
                    />
                </Grid>

                <Grid item xs={12} md={8}>
                    {loading ? (
                        <LinearProgress />
                    ) : selectedRun && yieldEstimate != null ? (
                        <TrackYieldInfo yieldEstimate={yieldEstimate} />
                    ) : (
                        <Typography variant="body1" mt={2}>
                            {selectedRun
                                ? "Failed to load yield."
                                : "Select a path run to view its yield info."}
                        </Typography>
                    )}
                </Grid>
            </Grid>
        </Container>
    );
}
