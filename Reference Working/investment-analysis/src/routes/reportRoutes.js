// ./src/routes/reportRoutes.js
const express = require('express');
const router = express.Router();
const reportController = require('../controllers/reportController');

router.post('/generate_report', reportController.generateReport);

module.exports = router;
