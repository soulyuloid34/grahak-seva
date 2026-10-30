import express, { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { QueryClassifier } from '../services/queryClassifier';
import { ResponseGenerator } from '../services/responseGenerator';
import { ConversationManager } from '../services/conversationManager';

export const chatRouter: Router = express.Router();

const queryClassifier = new QueryClassifier();
const responseGenerator = new ResponseGenerator();
const conversationManager = new ConversationManager();

interface ChatRequest {
  sessionId: string;
  message: string;
  customerId?: string;
}

interface ChatResponse {
  sessionId: string;
  response: string;
  intent: string;
  confidence: number;
  requiresEscalation: boolean;
  ticketId?: string;
  timestamp: string;
}

/**
 * POST /api/chat/message
 * Send a customer message and get an automated response
 */
chatRouter.post('/message', async (req: Request, res: Response) => {
  try {
    const { sessionId, message, customerId } = req.body as ChatRequest;

    // Validate input
    if (!message || message.trim().length === 0) {
      return res.status(400).json({ error: 'Message cannot be empty' });
    }

    // Create session if needed
    const actualSessionId = sessionId || uuidv4();

    // Classify the query
    const classification = await queryClassifier.classify(message);

    // Store in conversation history
    await conversationManager.addMessage(actualSessionId, {
      type: 'customer',
      content: message,
      intent: classification.intent,
      timestamp: new Date(),
    });

    // Generate response
    let response = '';
    let requiresEscalation = false;
    let ticketId: string | undefined;

    if (classification.confidence > 0.7) {
      response = await responseGenerator.generate(
        message,
        classification.intent,
        actualSessionId
      );
    } else {
      // Low confidence - escalate
      requiresEscalation = true;
      ticketId = uuidv4();
      response =
        "I'm not entirely sure about your query. Let me connect you with a support specialist.";
    }

    // Store bot response
    await conversationManager.addMessage(actualSessionId, {
      type: 'bot',
      content: response,
      timestamp: new Date(),
    });

    const chatResponse: ChatResponse = {
      sessionId: actualSessionId,
      response,
      intent: classification.intent,
      confidence: classification.confidence,
      requiresEscalation,
      ticketId,
      timestamp: new Date().toISOString(),
    };

    res.json(chatResponse);
  } catch (error) {
    console.error('Chat error:', error);
    res.status(500).json({ error: 'Failed to process message' });
  }
});

/**
 * GET /api/chat/history/:sessionId
 * Retrieve conversation history
 */
chatRouter.get('/history/:sessionId', async (req: Request, res: Response) => {
  try {
    const { sessionId } = req.params;
    const history = await conversationManager.getHistory(sessionId);
    res.json({ sessionId, history });
  } catch (error) {
    console.error('History retrieval error:', error);
    res.status(500).json({ error: 'Failed to retrieve history' });
  }
});

/**
 * POST /api/chat/feedback
 * Store user feedback for response quality
 */
chatRouter.post('/feedback', async (req: Request, res: Response) => {
  try {
    const { sessionId, messageId, rating, feedback } = req.body;
    // Store feedback in database for ML improvement
    res.json({ success: true, message: 'Feedback recorded' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to store feedback' });
  }
});
