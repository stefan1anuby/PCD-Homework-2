const express = require('express');
const app = express();
const http = require('http').Server(app);
const io = require('socket.io')(http);
const { Pool } = require('pg');
const path = require('path');
const port = 5000;

const pool = new Pool({
  user: process.env.PGUSER,
  host: process.env.PGHOST,
  database: process.env.PGDATABASE,
  password: process.env.PGPASSWORD,
  port: process.env.PGPORT,
});

app.get('/health', (req, res) => {
  res.status(200).send('OK');
});

app.get('/', function (req, res) {
  res.sendFile(path.join(__dirname, 'index.html'));
});

io.on('connection', async function (socket) {
  console.log('A user connected');

  try {
    const result = await pool.query('SELECT author, message FROM messages ORDER BY created_at ASC LIMIT 100');
    result.rows.forEach(row => {
      socket.emit('chat message', row.author, row.message);
    });
  } catch (err) {
    console.error('Error fetching messages:', err);
  }

  socket.on('disconnect', function () {
    console.log('A user disconnected');
  });

  socket.on('chat message', async function (author, message) {
    try {
      await pool.query('INSERT INTO messages(author, message) VALUES($1, $2)', [author, message]);
    } catch (err) {
      console.error('Error inserting message:', err);
    }

    io.emit('chat message', author, message);
  });
});

http.listen(port, function () {
  console.log('Listening on *:' + port);
});
