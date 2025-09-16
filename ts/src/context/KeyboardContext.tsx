import { createContext, useContext, useState, useRef, RefObject } from "react";
import { Modal } from "@mui/material";
import Keyboard from "react-simple-keyboard";
import "react-simple-keyboard/build/css/index.css";

type Setter = (value: string) => void;
type FieldRef = RefObject<HTMLInputElement>;

interface KeyboardContextProps {
    openKeyboard: (updateField: Setter, currentInputValue: string, ref?: FieldRef) => void
}

const KeyboardContext = createContext<KeyboardContextProps>({
    openKeyboard: () => {}
});

export const KeyboardProvider = ({ children }: { children: React.ReactNode }) => {
    const [showKeyboard, setShowKeyboard] = useState(false);
    const [inputValue,  setInputValue] = useState("");
    const setterRef = useRef<Setter>(() => {});
    const inputRef = useRef<FieldRef>();
    const keyboardRef = useRef<any>(null); 

    const openKeyboard = (updateField: Setter, currentInput: string, ref?: FieldRef) => {
        setterRef.current = updateField;
        inputRef.current = ref;
        setInputValue(currentInput);
        setShowKeyboard(true);
    };

    const handleKeyboardInput = (inputValue: string) => {
        setInputValue(inputValue);
        setterRef.current(inputValue);
        requestAnimationFrame(() => inputRef?.current?.current?.focus());
    };

    return (
        <KeyboardContext.Provider value={{ openKeyboard }}>
            {children}

            <Modal open={showKeyboard} onClose={() => setShowKeyboard(false)} BackdropProps={{ style: { backgroundColor: "transparent" } }} 
                sx={{
                    display: "flex",
                    alignItems: "flex-end", 
                    justifyContent: "center",
                    border: "none",
                }}
            >
                <Keyboard
                    keyboardRef={(r) => {
                        keyboardRef.current = r;
                        r?.setInput(inputValue);
                    }}
                    onChange={handleKeyboardInput}
                />
            </Modal>
        </KeyboardContext.Provider>
    );
};

export const useKeyboard = () => useContext(KeyboardContext);
