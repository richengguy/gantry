// A simple "hello world" nodejs app.

const http = require('http');
const process = require('process');
const port = 8080;

const server = http.createServer((_, res) => {
    console.log('Servicing request...');
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Hello World!');
});

process.on('SIGINT', () => {
    console.log('Received SIGINT signal...');
    process.exit(0);
});

server.listen(port, () => {
    console.log(`Server is listening on port ${port}.`);
});
