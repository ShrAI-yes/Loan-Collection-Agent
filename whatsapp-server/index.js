const express = require('express')
const bodyParser = require('body-parser')
const axios = require('axios')
const moment = require('moment')
require('dotenv').config()

const app = express().use(bodyParser.json())

const token = process.env.TOKEN
const mytoken = process.env.MYTOKEN
const flaskRAGUrl = process.env.FLASK_URL
const phoneNumberId = process.env.PHONE_NUMBER_ID

console.log("PHONE_NUMBER_ID:", phoneNumberId)

app.listen(8000, () => {
    console.log('webhook is listening on port 8000')
})

app.get('/', (req, res) => {
    res.status(200).send("The webhook is working.")
})

app.get('/webhook', (req, res) => {
    let mode = req.query["hub.mode"]
    let challenge = req.query["hub.challenge"]
    let token = req.query["hub.verify_token"]

    if (mode && token) {
        if (mode === "subscribe" && token === mytoken) {
            res.status(200).send(challenge)
        } else {
            res.status(403)
        }
    }
})

const recentMessages = new Set()

app.post("/webhook", (req, res) => {
    let body_param = req.body
    if (body_param.object) {
        if (body_param.entry &&
            body_param.entry[0].changes &&
            body_param.entry[0].changes[0].value &&
            body_param.entry[0].changes[0].value.messages &&
            body_param.entry[0].changes[0].value.messages[0]
        ) {
            let phone_no_id = body_param.entry[0].changes[0].value.metadata.phone_number_id
            let from = body_param.entry[0].changes[0].value.messages[0].from
            let msg_body = body_param.entry[0].changes[0].value.messages[0].text.body
            let messageId = body_param.entry[0].changes[0].value.messages[0].id

            if (!recentMessages.has(messageId)) {
                recentMessages.add(messageId)

                console.log("=====LOGS=====")
                console.log("Phone number ID:", phone_no_id)
                console.log("From:", from)
                console.log("Message body:", msg_body)
                console.log("Message ID:", messageId)
                console.log("=====LOGS=====")

                // Check if the message is "hi" (case-insensitive)  ==> this is the new requirement. this establishes a new session between the test number and the user for outbound llm messages i.e. the summary which is messgaed after the call ends. 
                if (msg_body.toLowerCase() === "hi") {
                    axios({
                        method: "POST",
                        url: `https://graph.facebook.com/v20.0/${phone_no_id}/messages?access_token=${token}`,
                        data: {
                            messaging_product: "whatsapp",
                            to: from,
                            text: {
                                body: "Hello! How can I assist you today?"
                            }
                        },
                        headers: {
                            "Content-Type": "application/json"
                        }
                    })
                    .then(response => {
                        console.log("Response sent successfully:", response.data)
                        markMessageAsRead(phone_no_id, messageId, token)
                    })
                    .catch(error => {
                        console.error("Error sending response:", error.response ? error.response.data : error.message)
                    })
                } else {
                    // Forward other messages to Flask RAG (existing behavior)  ==> this is not required in the current code.
                    axios.post(flaskRAGUrl, {
                        phone_number: from,
                        user_query: msg_body
                    })
                    .then(response => {
                        let flaskResponse = response.data.response
                        console.log("RAG Response:", flaskResponse)
                        return axios({
                            method: "POST",
                            url: `https://graph.facebook.com/v20.0/${phone_no_id}/messages?access_token=${token}`,
                            data: {
                                messaging_product: "whatsapp",
                                to: from,
                                text: {
                                    body: flaskResponse
                                }
                            },
                            headers: {
                                "Content-Type": "application/json"
                            }
                        })
                    })
                    .then(response => {
                        console.log("Message sent successfully:", response.data)
                        markMessageAsRead(phone_no_id, messageId, token)
                    })
                    .catch(error => {
                        console.error("Error communicating with Flask or sending message:", error.response ? error.response.data : error.message)
                    })
                }

                res.sendStatus(200)
            } else {
                console.log("Message already processed; ignoring.")
                res.sendStatus(200)
            }
        } else if (body_param.entry[0].changes[0].value.statuses) {
            const status = body_param.entry[0].changes[0].value.statuses[0]
            console.log("Message Status Update:", {
                messageId: status.id,
                status: status.status,
                recipient: status.recipient_id,
                timestamp: status.timestamp,
                error: status.errors ? status.errors[0] : null
            })
            res.sendStatus(200)
        } else {
            console.log("Received a status update, not a new message.")
            res.sendStatus(200)
        }
    } else {
        console.log("Not a valid WhatsApp webhook event.")
        res.sendStatus(400)
    }
})

app.post('/send-summary', async (req, res) => {
    const { phone_number, message } = req.body
    
    console.log("Sending summary with PHONE_NUMBER_ID:", phoneNumberId)
    
    try {
        if (!phoneNumberId) {
            throw new Error("PHONE_NUMBER_ID is not defined")
        }
        const response = await axios({
            method: "POST",
            url: `https://graph.facebook.com/v20.0/${phoneNumberId}/messages?access_token=${token}`,
            data: {
                messaging_product: "whatsapp",
                to: phone_number,
                text: {
                    body: message
                }
            },
            headers: {
                "Content-Type": "application/json"
            }
        })
        console.log("Summary sent successfully:", response.data)
        res.status(200).send({ success: true })
    } catch (error) {
        console.error("Error sending summary:", error.response ? error.response.data : error.message)
        res.status(500).send({ error: "Failed to send summary" })
    }
})

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
        console.log("Message marked as read successfully:", response.data)
    }).catch(error => {
        console.error("Error marking message as read:", error.response ? error.response.data : error.message)
    })
}