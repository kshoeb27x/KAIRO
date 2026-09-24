import { useEffect, useRef } from 'react';
import type { Message } from '../../../shared/types';

interface ConversationPanelProps {
  messages: Message[];
}

export function ConversationPanel({ messages }: ConversationPanelProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div className="conversation" role="log" aria-label="Conversation">
        <p className="conversation-empty">
          Ask JARVIS anything — try “What are we building today?”
        </p>
      </div>
    );
  }

  return (
    <div className="conversation" role="log" aria-label="Conversation">
      {messages.map((message) => (
        <div key={message.id} className={`msg ${message.role}`}>
          {message.content}
          {message.role === 'assistant' && (
            <span className="msg-meta">
              {message.provider ?? 'JARVIS'}
              {message.model ? ` · ${message.model}` : ''}
            </span>
          )}
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
