import { BrowserRouter, Route, Routes } from "react-router";
import './App.css'
import Home from './pages/Home'
import TrackSelect from './pages/TrackSelect'
import ViewCropYield from "./pages/ViewCropYield";
import { KeyboardProvider } from "./context/KeyboardContext";

function App() {

    return (
        <KeyboardProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<Home />}/>
                    <Route path="/TrackSelect" element={<TrackSelect />}/>
                    <Route path="/ViewCropYield" element={<ViewCropYield />}/>
                </Routes>
            </BrowserRouter>
        </KeyboardProvider>
    )
}

export default App
