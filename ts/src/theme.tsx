import { createTheme } from '@mui/material/styles';
import { } from '@mui/material/colors';

const theme = createTheme({
    palette: {
        mode: 'light',
        primary: {
            main: "#6feafc",
            contrastText: "#000"
        },
        secondary: {
            main: "#0055AA",
            contrastText: "#FFF"
        },
        background: {
            default: "#FFF"
        }
    },
});

export default theme;
