const express = require('express');
const app = express();
const http = require('http').Server(app);
const io = require('socket.io')(http);
const { Pool } = require('pg');
const path = require('path');
const port = 5000;
const { PubSub } = require('@google-cloud/pubsub');

app.use(express.json()); // Middleware to parse JSON requests

// PostgreSQL connection
const pool = new Pool({
  user: process.env.PGUSER,
  host: process.env.PGHOST,
  database: process.env.PGDATABASE,
  password: process.env.PGPASSWORD,
  port: process.env.PGPORT,
});

// Google Pub/Sub setup
const pubsub = new PubSub({ keyFilename: 'service-account.json' });
const topicName = 'projects/pcd-homework-2-455019/topics/eventarc-us-central1-trigger-vhayytoa-860';


// Serve HTML page
app.get('/', function (req, res) {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/health', (req, res) => {
  res.status(200).send('OK');
});


// Socket.io connection
io.on('connection', async function (socket) {
  console.log('A user connected');

  try {
    const result = await pool.query('SELECT author, message, label FROM messages ORDER BY created_at ASC LIMIT 100');
    result.rows.forEach(row => {
      console.log(`Message from ${row.author}: ${row.message} (Label: ${row.label})`);
      socket.emit('chat message', row.author, row.message, row.label);
    });

  } catch (err) {
    console.error('Error fetching messages:', err);
  }

  socket.on('disconnect', function () {
    console.log('A user disconnected');
  });

  socket.on('chat message', async function (author, message, label) {
    try {

      await pool.query('INSERT INTO messages(author, message) VALUES($1, $2)', [author, message]);
      // Publish message to Pub/Sub
      const messagePayload = { author, text: message, label };
      console.log('Message payload:', messagePayload);
      const dataBuffer = Buffer.from(JSON.stringify(messagePayload));
      const topic = pubsub.topic(topicName);
      await topic.publishMessage({ data: dataBuffer });

      console.log(`Message sent to Pub/Sub: ${author}: ${message}`);
    } catch (err) {
      console.error('Error insert message:', err);
    }
    io.emit('chat message', author, message);
  });

});


// Start server
http.listen(port, function () {
  console.log('Listening on *:' + port);
});

