import express, { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';

export const ticketRouter: Router = express.Router();

/**
 * POST /api/tickets
 * Create a support ticket
 */
ticketRouter.post('/', async (req: Request, res: Response) => {
  try {
    const { sessionId, reason, priority, customerId } = req.body;

    const ticketId = uuidv4();
    const ticket = {
      ticketId,
      sessionId,
      customerId,
      reason,
      priority,
      status: 'open',
      createdAt: new Date(),
      assignedTo: null,
    };

    // Save to database
    // await db.tickets.insert(ticket);

    res.status(201).json(ticket);
  } catch (error) {
    res.status(500).json({ error: 'Failed to create ticket' });
  }
});

/**
 * GET /api/tickets/:ticketId
 * Get ticket details
 */
ticketRouter.get('/:ticketId', async (req: Request, res: Response) => {
  try {
    const { ticketId } = req.params;
    // const ticket = await db.tickets.findById(ticketId);
    res.json({ ticketId, status: 'open' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to retrieve ticket' });
  }
});

/**
 * PUT /api/tickets/:ticketId
 * Update ticket status
 */
ticketRouter.put('/:ticketId', async (req: Request, res: Response) => {
  try {
    const { ticketId } = req.params;
    const { status, assignedTo } = req.body;
    // Update ticket
    res.json({ ticketId, status, assignedTo });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update ticket' });
  }
});
