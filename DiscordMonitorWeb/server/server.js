const express = require('express')
const bodyParser = require('body-parser')
const cors = require('cors')

const passport = require('passport');


const db = require('./db')
const router = require('./routes')

const app = express()
const apiPort = 3000

app.use(passport.initialize());
app.use(bodyParser.urlencoded({ extended: true }))
app.use(cors())
app.use(bodyParser.json())

app.use(function(req, res, next) {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE");
    res.header(
        "Access-Control-Allow-Headers",
        "Content-type,Accept,x-access-token,X-Key"
    );
    if (req.method == "OPTIONS") {
        res.status(200).end();
    } else {
        next();
    }
});

db.on('error', console.error.bind(console, 'MongoDB connection error:'))

app.get('/', (req, res) => {
    res.send('Welcome')
})

app.use('/api', router)

app.listen(apiPort, () => console.log(`Server running on port ${apiPort}`))