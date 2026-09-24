import type { FastifyReply } from 'fastify';

/**
 * Normalized safe API errors. Stack traces are never sent to the browser;
 * in production only the safe message leaves the server.
 */
export function sendError(
  reply: FastifyReply,
  statusCode: number,
  code: string,
  message: string,
): FastifyReply {
  return reply.status(statusCode).send({ error: { code, message } });
}
