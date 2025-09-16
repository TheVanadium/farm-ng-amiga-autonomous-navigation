import { Button } from "@mui/material";
import { useNavigate } from "react-router";

export default function BackButton() {
    const navigate = useNavigate();
    function handleClick() {
        navigate(-1);
    }
    return (
        <Button
            variant="contained"
            style={{ width: "100px", fontSize: "30px" }}
            onClick={handleClick}
        >
            ⬅
        </Button>
    );
}
