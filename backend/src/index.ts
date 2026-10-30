import express, { Express, Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { chatRouter } from './routes/chat';
import { ticketRouter } from './routes/tickets';
import { analyticsRouter } from './routes/analytics';
import { errorHandler } from './middleware/errorHandler';
import { requestLogger } from './middleware/logger';

dotenv.config();

const app: Express = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(requestLogger);

// Routes
app.use('/api/chat', chatRouter);
app.use('/api/tickets', ticketRouter);
app.use('/api/analytics', analyticsRouter);

// Health check
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 404 handler
app.use((req: Request, res: Response) => {
  res.status(404).json({ error: 'Route not found' });
});

// Error handler (must be last)
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
  console.log(`📊 API Documentation at http://localhost:${PORT}/api-docs`);
});

export default app;
