import { Button } from "@mui/material";
import React, { useState, useEffect } from "react";

const ExitButton: React.FC = () => {
    const [appData, setAppData] = useState<{ [key: string]: any }>({});

    const handleClick = () => {
        const baseEndpoint = `http://${window.location.hostname}:8001/systemctl_action/`;
        const killEndpoint = `${import.meta.env.VITE_API_URL}/kill`;

        // Close the python server
        fetch(killEndpoint, { method: "GET" });

        const requestBody = {
            account_name: appData.account,
            service_id: appData.name,
            action: "stop",
            app_route: appData.app_route,
        };

        // request server start the service
        fetch(baseEndpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
        })
        .then((response) => response.json())
        .then((result) => {
            console.log("Service action response:", result);
            // redirect
        })
        .catch((error) => {
            console.error("Error:", error);
        }).finally(() => {
            window.location.href = `${window.location.protocol}//${window.location.hostname}/apps/launcher`;
        });
    };

    useEffect(() => {
        const baseEndpoint = `http://${window.location.hostname}:8001/custom_app_info/${window.location.port}`;

        fetch(baseEndpoint)
            .then((response) => response.json())
            .then((result) => {
                if (result) {
                    setAppData(result.service);
                }
            });
    }, []);

    return (
        <Button
            variant="contained"
            style={{ width: "100px", fontSize: "30px" }}
            onClick={handleClick}
        >
            ⬅
        </Button>
    );
};

export default ExitButton;
