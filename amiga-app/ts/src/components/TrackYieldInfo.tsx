import { Box, Typography } from "@mui/material";

interface TrackYieldInfoProps {
  yieldEstimate: number;
}

export default function TrackYieldInfo({ yieldEstimate }: TrackYieldInfoProps) {
  return (
    <Box
      sx={{
        border: "2px solid black",
        borderRadius: 4,
        p: 4,
        width: "100%",
        maxWidth: 400,
        mt: 2,
      }}
    >
      <Typography variant="h6" gutterBottom>
        Estimated Crop Yield
      </Typography>
      <Typography variant="h3">
        {yieldEstimate.toFixed(2)} g
      </Typography>
    </Box>
  );
}

