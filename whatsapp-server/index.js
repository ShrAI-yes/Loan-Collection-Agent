const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
require('dotenv').config();

const app = express().use(bodyParser.json());

const token = process.env.TOKEN;
const mytoken = process.env.MYTOKEN;
const flaskUrl = 'http://localhost:5000'; // Points to server.py
const phoneNumberId = process.env.PHONE_NUMBER_ID;

console.log("PHONE_NUMBER_ID:", phoneNumberId);

app.listen(8000, () => {
    console.log('Webhook is listening on port 8000');
});

app.get('/', (req, res) => {
    res.status(200).send("The webhook is working.");
});

app.get('/webhook', (req, res) => {
    let mode = req.query["hub.mode"];
    let challenge = req.query["hub.challenge"];
    let token = req.query["hub.verify_token"];

    if (mode && token) {
        if (mode === "subscribe" && token === mytoken) {
            res.status(200).send(challenge);
        } else {
            res.status(403);
        }
    }
});

const recentMessages = new Set();

app.post("/webhook", async (req, res) => {
    let body_param = req.body;
    if (body_param.object) {
        if (
            body_param.entry &&
            body_param.entry[0].changes &&
            body_param.entry[0].changes[0].value &&
            body_param.entry[0].changes[0].value.messages &&
            body_param.entry[0].changes[0].value.messages[0]
        ) {
            let phone_no_id = body_param.entry[0].changes[0].value.metadata.phone_number_id;
            let from = body_param.entry[0].changes[0].value.messages[0].from;
            let msg_body = body_param.entry[0].changes[0].value.messages[0].text.body;
            let messageId = body_param.entry[0].changes[0].value.messages[0].id;

            if (!recentMessages.has(messageId)) {
                recentMessages.add(messageId);

                console.log("=====LOGS=====");
                console.log("Phone number ID:", phone_no_id);
                console.log("From:", from);
                console.log("Message body:", msg_body);
                console.log("Message ID:", messageId);
                console.log("=====LOGS=====");

                try {
                    if (msg_body.toLowerCase() === "hi") {
                        // Hardcoded response for "hi"
                        await axios({
                            method: "POST",
                            url: `https://graph.facebook.com/v20.0/${phone_no_id}/messages?access_token=${token}`,
                            data: {
                                messaging_product: "whatsapp",
                                to: from,
                                text: { body: "Hello! How can I assist you today?" }
                            },
                            headers: { "Content-Type": "application/json" }
                        });
                        console.log("Sent hardcoded response for 'hi' to", from);
                        markMessageAsRead(phone_no_id, messageId, token);

                        // Notify Flask of 'delivered' status
                        await axios.post(`${flaskUrl}/update-whatsapp-status`, {
                            phone: from,
                            status: "delivered"
                        });
                    } else {
                        // Forward other messages to Flask for Agent.py processing
                        const response = await axios.post(`${flaskUrl}/process-whatsapp-message`, {
                            phone_number: from,
                            user_query: msg_body
                        });

                        const aiResponse = response.data.response;
                        console.log("AI Response:", aiResponse);

                        // Send AI response back to WhatsApp
                        await axios({
                            method: "POST",
                            url: `https://graph.facebook.com/v20.0/${phone_no_id}/messages?access_token=${token}`,
                            data: {
                                messaging_product: "whatsapp",
                                to: from,
                                text: { body: aiResponse }
                            },
                            headers: { "Content-Type": "application/json" }
                        });

                        console.log("Response sent successfully to", from);
                        markMessageAsRead(phone_no_id, messageId, token);

                        // Notify Flask of 'delivered' status
                        await axios.post(`${flaskUrl}/update-whatsapp-status`, {
                            phone: from,
                            status: "delivered"
                        });
                    }
                } catch (error) {
                    console.error("Error processing message:", error.response ? error.response.data : error.message);
                }

                res.sendStatus(200);
            } else {
                console.log("Message already processed; ignoring.");
                res.sendStatus(200);
            }
        } else if (body_param.entry[0].changes[0].value.statuses) {
            const status = body_param.entry[0].changes[0].value.statuses[0];
            console.log("Message Status Update:", {
                messageId: status.id,
                status: status.status,
                recipient: status.recipient_id,
                timestamp: status.timestamp,
                error: status.errors ? status.errors[0] : null
            });

            // Notify Flask of status update
            try {
                await axios.post(`${flaskUrl}/update-whatsapp-status`, {
                    phone: status.recipient_id,
                    status: status.status
                });
            } catch (error) {
                console.error("Error updating status:", error.response ? error.response.data : error.message);
            }

            res.sendStatus(200);
        } else {
            console.log("Received a status update, not a new message.");
            res.sendStatus(200);
        }
    } else {
        console.log("Not a valid WhatsApp webhook event.");
        res.sendStatus(400);
    }
});

app.post('/send-summary', async (req, res) => {
    const { phone_number, message } = req.body;
    
    console.log("Sending summary with PHONE_NUMBER_ID:", phoneNumberId);
    
    try {
        if (!phoneNumberId) {
            throw new Error("PHONE_NUMBER_ID is not defined");
        }
        const response = await axios({
            method: "POST",
            url: `https://graph.facebook.com/v20.0/${phoneNumberId}/messages?access_token=${token}`,
            data: {
                messaging_product: "whatsapp",
                to: phone_number,
                text: { body: message }
            },
            headers: { "Content-Type": "application/json" }
        });
        console.log("Summary sent successfully:", response.data);

        // Notify Flask of 'sent' status
        await axios.post(`${flaskUrl}/update-whatsapp-status`, {
            phone: phone_number,
            status: "sent"
        });

        res.status(200).send({ success: true });
    } catch (error) {
        console.error("Error sending summary:", error.response ? error.response.data : error.message);
        res.status(500).send({ error: "Failed to send summary" });
    }
});

const markMessageAsRead = (phone_no_id, messageId, token) => {
    axios({
        method: "POST",
        url: `https://graph.facebook.com/v20.0/${phone_no_id}/messages`,
        data: {
            messaging_product: "whatsapp",
            status: "read",
            message_id: messageId
        },
        headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        }
    }).then(response => {
        console.log("Message marked as read successfully:", response.data);
    }).catch(error => {
        console.error("Error marking message as read:", error.response ? error.response.data : error.message);
    });
};