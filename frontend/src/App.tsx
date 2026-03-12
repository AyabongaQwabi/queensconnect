import { useState, useEffect, useRef } from 'react';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { TypingIndicator } from './components/TypingIndicator';
import { InteractiveBlock } from './components/InteractiveBlock';

const STORAGE_KEY = 'queens_connect_chat';
const WA_NUMBER_KEY = 'queens_connect_wa_number';
const SAVED_SESSIONS_KEY = 'queens_connect_saved_sessions';
const LANGUAGE_PREF_KEY = 'queens_connect_language_pref';
const WELCOME =
  "Hi! 👋 I'm Queens Connect. Ask me about local businesses, cabs, events, or anything in your area. What would you like to do? 😊";
const ERROR_MSG =
  'Something went wrong on our side — please try again in a moment.';

const QUICK_ACTIONS = [
  'Find a cab',
  'Get a loan',
  'Loan a person',
  'Open a stokvel',
  'Join a stokvel',
  'Create / get my CV',
  'Find an expert',
  'Find some info',
  'Find lost item',
  'Add a lost item',
  'See events',
  'See news',
  'Add an event',
  'Create a stokvel',
  'File complaint',
  'List complaints',
];

/** Item-creation actions shown only when admin WA number is logged in */
const ADMIN_QUICK_ACTIONS = [
  'Add taxi price',
  'Add info',
  'Create a Listing',
  'Add place',
  'List event',
  'Add a cab driver',
];

const ADMIN_WA_NUMBER = '27603116777';

function isAdminUser(waNumber: string): boolean {
  const digits = (waNumber || '').replace(/\D/g, '');
  return digits === ADMIN_WA_NUMBER;
}

const QUICK_ACTION_PHRASES: Record<string, string> = {
  'Get a loan': 'I’d like to get a loan.',
  'Add taxi price': 'I’d like to share local taxi prices.',
  'Loan a person': 'I’d like to loan money to someone.',
  'Find some info': 'I’d like to find some community info.',
  'Add info': 'I’d like to share some community info.',
  'Open a stokvel': 'I’d like to open a stokvel.',
  'Join a stokvel': 'I’d like to join a stokvel.',
  'Create a stokvel': "I'd like to create a stokvel.",
  'Create a Listing': 'I’d like to create a community listing.',
  'Find an expert':
    'I’d like to find a listing for a local expert or technician',
  'Add place': "I'd like to add a place.",
  'Find place': "I'd like to find a place.",
  'Find lost item': 'I’d like to find a lost item.',
  'Add a lost item': 'I’d like to add a lost item.',
  'See events': 'I’d like to see community events.',
  'See news': "I'd like to see the latest news.",
  'Add an event': 'I’d like to add a community event.',
  'File complaint': 'I’d like to file a community complaint.',
  'List complaints': 'I’d like to see complaints I’ve filed.',
  'Add a cab driver': "I'd like to add a cab driver.",
  'Find a cab': "I'd like to find a cab.",
  'Create / get my CV': "I'd like to create or get my CV.",
};

const LANGUAGE_OPTIONS = [
  { value: 'english', label: 'English' },
  { value: 'xhosa', label: 'Xhosa' },
  { value: 'mix', label: 'English + Xhosa Mix' },
  { value: 'xhosa_light_kasi', label: 'Full Xhosa / Light kasi' },
] as const;
type LanguagePref = (typeof LANGUAGE_OPTIONS)[number]['value'];

function getStoredLanguagePref(): LanguagePref {
  try {
    const stored = localStorage.getItem(LANGUAGE_PREF_KEY);
    if (stored && LANGUAGE_OPTIONS.some((o) => o.value === stored))
      return stored as LanguagePref;
  } catch {
    // ignore
  }
  return 'english';
}

export type InteractiveOption = { value: string; label: string };

export type InteractiveSpec = {
  type: 'buttons' | 'dropdown' | 'radio' | 'checkboxes' | 'link';
  name: string;
  label?: string | null;
  options: InteractiveOption[];
  submitLabel?: string | null;
};

type Message = {
  role: 'user' | 'assistant';
  content: string;
  responseTimeMs?: number;
  interactive?: InteractiveSpec | null;
};

type SavedSession = {
  id: string;
  name: string;
  waNumber: string;
  messages: Message[];
  savedAt: string;
};

function getSavedSessions(): SavedSession[] {
  try {
    const raw = localStorage.getItem(SAVED_SESSIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedSession[];
    if (!Array.isArray(parsed)) return [];
    return parsed.sort(
      (a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime(),
    );
  } catch {
    return [];
  }
}

function saveSessionToStore(
  name: string | undefined,
  waNumber: string,
  messages: Message[],
): SavedSession {
  const id =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : 'sess_' + Date.now();
  const savedAt = new Date().toISOString();
  const displayName =
    name?.trim() || '' || 'Session ' + new Date().toLocaleString();
  const session: SavedSession = {
    id,
    name: displayName,
    waNumber,
    messages,
    savedAt,
  };
  const list = getSavedSessions();
  list.unshift(session);
  try {
    localStorage.setItem(SAVED_SESSIONS_KEY, JSON.stringify(list));
  } catch {
    // ignore
  }
  return session;
}

function loadSessionFromStore(id: string): Message[] | null {
  const list = getSavedSessions();
  const session = list.find((s) => s.id === id);
  if (!session) return null;
  try {
    localStorage.setItem(WA_NUMBER_KEY, session.waNumber);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session.messages));
  } catch {
    return null;
  }
  return session.messages;
}

function deleteSavedSession(id: string): void {
  const list = getSavedSessions().filter((s) => s.id !== id);
  try {
    localStorage.setItem(SAVED_SESSIONS_KEY, JSON.stringify(list));
  } catch {
    // ignore
  }
}

function clearAllSessions(): void {
  try {
    localStorage.setItem(SAVED_SESSIONS_KEY, '[]');
  } catch {
    // ignore
  }
}

function getWaNumber(): string {
  try {
    const stored = localStorage.getItem(WA_NUMBER_KEY);
    if (stored) return stored;
    return '';
  } catch {
    return '';
  }
}

/** True if we have a user-provided WhatsApp number (not placeholder). Required before chat. */
function hasValidWaNumber(wa: string): boolean {
  if (!wa || wa.startsWith('web_')) return false;
  const digits = wa.replace(/\D/g, '');
  return digits.length >= 10;
}

function loadMessages(): Message[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [{ role: 'assistant', content: WELCOME }];
    const parsed = JSON.parse(raw) as Message[];
    if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    return [{ role: 'assistant', content: WELCOME }];
  } catch {
    return [{ role: 'assistant', content: WELCOME }];
  }
}

function saveMessages(messages: Message[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  } catch {
    // ignore
  }
}

function getConversationTitle(messages: Message[]): string {
  const firstUser = messages.find((m) => m.role === 'user');
  if (firstUser?.content) {
    const text = firstUser.content.trim();
    return text.length > 60 ? text.slice(0, 60) + '…' : text;
  }
  return 'New chat';
}

const API_URL = import.meta.env.VITE_API_URL || 'https://qwabi.co.za';

function AdminPanel({ apiUrl }: { apiUrl: string }) {
  const [lenderWa, setLenderWa] = useState('');
  const [lenderName, setLenderName] = useState('');
  const [lenderIdNumber, setLenderIdNumber] = useState('');
  const [lenderAddress, setLenderAddress] = useState('');
  const [lenderLoading, setLenderLoading] = useState(false);
  const [lenderMessage, setLenderMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);
  const [borrowerWa, setBorrowerWa] = useState('');
  const [borrowerName, setBorrowerName] = useState('');
  const [borrowerIdNumber, setBorrowerIdNumber] = useState('');
  const [borrowerAddress, setBorrowerAddress] = useState('');
  const [borrowerLoading, setBorrowerLoading] = useState(false);
  const [borrowerMessage, setBorrowerMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const submitLender = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lenderWa.trim() || !lenderName.trim()) return;
    setLenderMessage(null);
    setLenderLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/lenders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wa_number: lenderWa.trim(),
          display_name: lenderName.trim(),
          id_number: lenderIdNumber.trim() || undefined,
          address: lenderAddress.trim() || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.status === 'success') {
        setLenderMessage({
          type: 'success',
          text: `Lender created: ${data.lenderUid}`,
        });
        setLenderWa('');
        setLenderName('');
        setLenderIdNumber('');
        setLenderAddress('');
      } else {
        setLenderMessage({
          type: 'error',
          text:
            res.status === 400
              ? (data.detail ?? 'Failed')
              : (data.error_message ?? 'Failed to create lender'),
        });
      }
    } catch {
      setLenderMessage({ type: 'error', text: 'Network error' });
    } finally {
      setLenderLoading(false);
    }
  };

  const submitBorrower = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!borrowerWa.trim() || !borrowerName.trim()) return;
    setBorrowerMessage(null);
    setBorrowerLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/borrowers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wa_number: borrowerWa.trim(),
          display_name: borrowerName.trim(),
          id_number: borrowerIdNumber.trim() || undefined,
          address: borrowerAddress.trim() || undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.status === 'success') {
        setBorrowerMessage({
          type: 'success',
          text: `Borrower created: ${data.borrowerUid}`,
        });
        setBorrowerWa('');
        setBorrowerName('');
        setBorrowerIdNumber('');
        setBorrowerAddress('');
      } else {
        setBorrowerMessage({
          type: 'error',
          text:
            res.status === 400
              ? (data.detail ?? 'Failed')
              : (data.error_message ?? 'Failed to create borrower'),
        });
      }
    } catch {
      setBorrowerMessage({ type: 'error', text: 'Network error' });
    } finally {
      setBorrowerLoading(false);
    }
  };

  return (
    <div className='flex-1 flex flex-col bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden min-h-0'>
      <div className='px-4 sm:px-5 py-4 border-b border-gray-100 shrink-0'>
        <h2 className='text-base sm:text-lg font-semibold text-gray-900'>
          Add lenders & borrowers
        </h2>
        <p className='text-sm text-gray-500 mt-0.5'>
          Create lender or borrower profiles (e.g. for testing or manual
          onboarding).
        </p>
      </div>
      <div className='flex-1 overflow-y-auto p-4 sm:p-6 grid gap-4 sm:gap-6 sm:grid-cols-2 min-h-0'>
        <section className='rounded-xl border border-gray-200 bg-gray-50/50 p-5'>
          <h3 className='text-base font-medium text-gray-800 mb-4'>
            Add lender
          </h3>
          <form onSubmit={submitLender} className='space-y-4'>
            <div>
              <label
                htmlFor='lender-wa'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                WhatsApp number / ID
              </label>
              <input
                id='lender-wa'
                type='text'
                value={lenderWa}
                onChange={(e) => setLenderWa(e.target.value)}
                placeholder='e.g. 27821234567 or web_test_1'
                className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-1 focus:ring-[#7c3aed]'
              />
            </div>
            <div>
              <label
                htmlFor='lender-name'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                Full name and surname
              </label>
              <input
                id='lender-name'
                type='text'
                value={lenderName}
                onChange={(e) => setLenderName(e.target.value)}
                placeholder='e.g. Sipho Ngcobo'
                className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-1 focus:ring-[#7c3aed]'
              />
            </div>
            <div>
              <label
                htmlFor='lender-id'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                South African ID number (13 digits)
              </label>
              <input
                id='lender-id'
                type='text'
                value={lenderIdNumber}
                onChange={(e) => setLenderIdNumber(e.target.value)}
                placeholder='e.g. 9001015001087'
                maxLength={13}
                className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-1 focus:ring-[#7c3aed]'
              />
            </div>
            <div>
              <label
                htmlFor='lender-address'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                Physical address
              </label>
              <input
                id='lender-address'
                type='text'
                value={lenderAddress}
                onChange={(e) => setLenderAddress(e.target.value)}
                placeholder='e.g. 123 Ezibeleni, Zone 3, Komani'
                className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-1 focus:ring-[#7c3aed]'
              />
            </div>
            {lenderMessage && (
              <p
                className={`text-sm ${lenderMessage.type === 'success' ? 'text-emerald-600' : 'text-red-600'}`}
              >
                {lenderMessage.text}
              </p>
            )}
            <button
              type='submit'
              disabled={lenderLoading || !lenderWa.trim() || !lenderName.trim()}
              className='w-full rounded-xl bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 text-sm transition-colors'
            >
              {lenderLoading ? 'Creating…' : 'Create lender'}
            </button>
          </form>
        </section>
        <section className='rounded-xl border border-gray-200 bg-gray-50/50 p-5'>
          <h3 className='text-base font-medium text-gray-800 mb-4'>
            Add borrower
          </h3>
          <form onSubmit={submitBorrower} className='space-y-4'>
            <div>
              <label
                htmlFor='borrower-wa'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                WhatsApp number / ID
              </label>
              <input
                id='borrower-wa'
                type='text'
                value={borrowerWa}
                onChange={(e) => setBorrowerWa(e.target.value)}
                placeholder='e.g. 27821234567 or web_test_1'
                className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-1 focus:ring-[#7c3aed]'
              />
            </div>
            <div>
              <label
                htmlFor='borrower-name'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                Full name and surname
              </label>
              <input
                id='borrower-name'
                type='text'
                value={borrowerName}
                onChange={(e) => setBorrowerName(e.target.value)}
                placeholder='e.g. Awonke S.'
                className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-1 focus:ring-[#7c3aed]'
              />
            </div>
            <div>
              <label
                htmlFor='borrower-id'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                South African ID number (13 digits)
              </label>
              <input
                id='borrower-id'
                type='text'
                value={borrowerIdNumber}
                onChange={(e) => setBorrowerIdNumber(e.target.value)}
                placeholder='e.g. 9001015001087'
                maxLength={13}
                className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-1 focus:ring-[#7c3aed]'
              />
            </div>
            <div>
              <label
                htmlFor='borrower-address'
                className='block text-sm font-medium text-gray-700 mb-1'
              >
                Physical address
              </label>
              <input
                id='borrower-address'
                type='text'
                value={borrowerAddress}
                onChange={(e) => setBorrowerAddress(e.target.value)}
                placeholder='e.g. 123 Ezibeleni, Zone 3, Komani'
                className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-1 focus:ring-[#7c3aed]'
              />
            </div>
            {borrowerMessage && (
              <p
                className={`text-sm ${borrowerMessage.type === 'success' ? 'text-emerald-600' : 'text-red-600'}`}
              >
                {borrowerMessage.text}
              </p>
            )}
            <button
              type='submit'
              disabled={
                borrowerLoading || !borrowerWa.trim() || !borrowerName.trim()
              }
              className='w-full rounded-xl bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 text-sm transition-colors'
            >
              {borrowerLoading ? 'Creating…' : 'Create borrower'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

type ViewMode = 'chat' | 'admin';

export default function App() {
  const [messages, setMessages] = useState<Message[]>(loadMessages);
  const [isLoading, setIsLoading] = useState(false);
  const [savedSessions, setSavedSessions] =
    useState<SavedSession[]>(getSavedSessions);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [saveFeedback, setSaveFeedback] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('chat');
  const listRef = useRef<HTMLDivElement>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const [languagePref, setLanguagePref] = useState<LanguagePref>(
    getStoredLanguagePref,
  );
  const [languageDropdownOpen, setLanguageDropdownOpen] = useState(false);
  const languageRef = useRef<HTMLDivElement>(null);
  const [waNumber, setWaNumberState] = useState(getWaNumber);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [preChatWaInput, setPreChatWaInput] = useState('');
  const [preChatError, setPreChatError] = useState<string | null>(null);
  const hasWa = hasValidWaNumber(waNumber);

  useEffect(() => {
    saveMessages(messages);
  }, [messages]);

  // Load persisted chat history from backend when we have a valid wa_number
  useEffect(() => {
    if (!hasWa || !waNumber) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${API_URL}/chats/${encodeURIComponent(waNumber)}/messages`,
        );
        const data = await res.json().catch(() => ({}));
        const list = data.messages as
          | Array<{
              sender: string;
              text: string;
              timestamp?: string;
              metadata?: { interactive?: InteractiveSpec };
            }>
          | undefined;
        if (cancelled || !Array.isArray(list)) return;
        const next: Message[] =
          list.length === 0
            ? [{ role: 'assistant', content: WELCOME }]
            : list.map((m) => ({
                role: m.sender === 'user' ? 'user' : 'assistant',
                content: m.text ?? '',
                interactive: m.metadata?.interactive ?? undefined,
              }));
        setMessages(next);
      } catch {
        // keep existing messages (e.g. from localStorage)
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [waNumber, hasWa]);

  useEffect(() => {
    listRef.current?.scrollTo(0, listRef.current.scrollHeight);
  }, [messages, isLoading]);

  useEffect(() => {
    setSavedSessions(getSavedSessions());
  }, [messages]);

  useEffect(() => {
    if (saveFeedback === null) return;
    const t = setTimeout(() => setSaveFeedback(null), 2000);
    return () => clearTimeout(t);
  }, [saveFeedback]);

  useEffect(() => {
    try {
      localStorage.setItem(LANGUAGE_PREF_KEY, languagePref);
    } catch {
      // ignore
    }
  }, [languagePref]);

  useEffect(() => {
    if (!languageDropdownOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (
        languageRef.current &&
        !languageRef.current.contains(e.target as Node)
      ) {
        setLanguageDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [languageDropdownOpen]);

  const handleNewSession = () => {
    // Start a fresh chat and force the user to enter a new WhatsApp number
    try {
      localStorage.removeItem(WA_NUMBER_KEY);
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify([{ role: 'assistant', content: WELCOME }]),
      );
    } catch {
      // ignore storage errors
    }
    setWaNumberState('');
    setPreChatWaInput('');
    setPreChatError(null);
    setMessages([{ role: 'assistant', content: WELCOME }]);
    setActiveSessionId(null);
    setSidebarOpen(false);
  };

  const handlePreChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const v = preChatWaInput.trim();
    if (!v) {
      setPreChatError('Please enter your WhatsApp number.');
      return;
    }
    const digits = v.replace(/\D/g, '');
    let national: string;
    if (digits.startsWith('27')) {
      national = digits.slice(2);
    } else if (digits.startsWith('0')) {
      national = digits.slice(1);
    } else {
      national = digits;
    }
    if (!/^[1-9][0-9]{8}$/.test(national)) {
      setPreChatError(
        'Please enter a valid WhatsApp number in the format +27XXXXXXXXX (e.g. +27603116777). It must not start with 0.',
      );
      return;
    }
    const normalized = `+27${national}`;
    setPreChatError(null);
    try {
      localStorage.setItem(WA_NUMBER_KEY, normalized);
      setWaNumberState(normalized);
      setPreChatWaInput('');
    } catch {
      setPreChatError('Could not save. Please try again.');
    }
  };

  const handleQuickAction = (action: string) => {
    const message = QUICK_ACTION_PHRASES[action] ?? action;
    handleSend(message);
  };

  const handleSaveSession = () => {
    const name = window.prompt(
      'Name this session (optional):',
      getConversationTitle(messages),
    );
    const waNumber = getWaNumber();
    const session = saveSessionToStore(name ?? undefined, waNumber, messages);
    setSavedSessions(getSavedSessions());
    setSaveFeedback('Saved as ' + session.name);
    setActiveSessionId(session.id);
  };

  const handleOpenSession = (id: string) => {
    const loaded = loadSessionFromStore(id);
    if (loaded !== null) {
      setMessages(loaded);
      setActiveSessionId(id);
      setWaNumberState(getWaNumber());
    }
    setSavedSessions(getSavedSessions());
    setSidebarOpen(false);
  };

  const handleDeleteSession = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    deleteSavedSession(id);
    setSavedSessions(getSavedSessions());
    if (activeSessionId === id) {
      setActiveSessionId(null);
      handleNewSession();
    }
  };

  const handleClearAllSessions = () => {
    if (window.confirm('Clear all saved sessions? This cannot be undone.')) {
      clearAllSessions();
      setSavedSessions([]);
      setActiveSessionId(null);
      handleNewSession();
    }
  };

  const handleSend = async (content: string) => {
    const userMessage: Message = { role: 'user', content };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    const start = performance.now();

    const tryStream = async () => {
      const res = await fetch(`${API_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wa_number: getWaNumber(),
          message: content,
          language_pref: languagePref,
        }),
      });
      if (!res.ok || !res.body) return null;
      return res;
    };

    try {
      const res = await tryStream();
      if (res?.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6)) as {
                  text?: string;
                  done?: boolean;
                  reply?: string;
                  responseTimeMs?: number;
                  error?: string;
                  interactive?: InteractiveSpec | null;
                };
                if (data.error != null) {
                  setMessages((prev) => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last?.role === 'assistant')
                      next[next.length - 1] = {
                        ...last,
                        content: data.reply ?? ERROR_MSG,
                      };
                    return next;
                  });
                  break;
                }
                if (data.text != null) {
                  setMessages((prev) => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last?.role === 'assistant')
                      next[next.length - 1] = {
                        ...last,
                        content: last.content + data.text,
                      };
                    return next;
                  });
                }
                if (data.done === true) {
                  const reply = data.reply ?? '';
                  const responseTimeMs =
                    data.responseTimeMs ??
                    Math.round(performance.now() - start);
                  const interactive =
                    data.interactive != null
                      ? (data.interactive as InteractiveSpec)
                      : undefined;
                  setMessages((prev) => {
                    const next = [...prev];
                    const last = next[next.length - 1];
                    if (last?.role === 'assistant')
                      next[next.length - 1] = {
                        ...last,
                        content: reply,
                        responseTimeMs,
                        interactive,
                      };
                    return next;
                  });
                }
              } catch {
                // ignore malformed JSON
              }
            }
          }
        }
      } else {
        const resNonStream = await fetch(`${API_URL}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            wa_number: getWaNumber(),
            message: content,
            language_pref: languagePref,
          }),
        });
        const data = await resNonStream.json().catch(() => ({}));
        const reply =
          resNonStream.ok && data.reply != null ? data.reply : ERROR_MSG;
        const responseTimeMs = Math.round(performance.now() - start);
        const interactive =
          resNonStream.ok && data.interactive != null
            ? (data.interactive as InteractiveSpec)
            : undefined;
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: reply, responseTimeMs, interactive },
        ]);
      }
    } catch {
      const responseTimeMs = Math.round(performance.now() - start);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: ERROR_MSG, responseTimeMs },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className='h-screen max-h-[100dvh] bg-[#e8ecf4] flex items-center justify-center px-3 sm:px-6 py-4'>
      {/* Mobile/desktop sidebar backdrop */}
      {sidebarOpen && (
        <button
          type='button'
          aria-label='Close menu'
          className='fixed inset-0 bg-black/40 z-30'
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className='relative w-full max-w-5xl flex items-stretch'>
        {/* Left sidebar: always a slide-in drawer, hidden by default */}
        <aside
          ref={sidebarRef}
          className={`
          fixed inset-y-0 left-0 z-40 w-64 shrink-0 flex flex-col bg-white border-r border-gray-200
          rounded-r-2xl shadow-sm overflow-hidden
          transform transition-transform duration-200 ease-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
        >
          <div className='p-4 border-b border-gray-100 flex items-center justify-between md:block'>
            <h1 className='text-lg font-bold text-gray-900 tracking-tight'>
              Queens Connect
            </h1>
            <button
              type='button'
              aria-label='Close menu'
              className='md:hidden p-2 -mr-2 rounded-lg text-gray-500 hover:bg-gray-100'
              onClick={() => setSidebarOpen(false)}
            >
              <svg
                className='w-5 h-5'
                fill='none'
                stroke='currentColor'
                viewBox='0 0 24 24'
                aria-hidden
              >
                <path
                  strokeLinecap='round'
                  strokeLinejoin='round'
                  strokeWidth={2}
                  d='M6 18L18 6M6 6l12 12'
                />
              </svg>
            </button>
          </div>
          <div className='p-4 pt-0 border-b border-gray-100 md:border-b'>
            <button
              type='button'
              onClick={handleNewSession}
              className='mt-3 w-full flex items-center justify-center gap-2 rounded-xl bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-medium py-2.5 text-sm transition-colors'
            >
              <span className='text-lg leading-none'>+</span>
              New chat
            </button>
            <button
              type='button'
              onClick={() => {
                setViewMode(viewMode === 'admin' ? 'chat' : 'admin');
                setSidebarOpen(false);
              }}
              className={`mt-2 w-full flex items-center justify-center gap-2 rounded-xl font-medium py-2.5 text-sm transition-colors ${
                viewMode === 'admin'
                  ? 'bg-gray-200 text-gray-800'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200'
              }`}
            >
              {viewMode === 'admin'
                ? '← Back to chat'
                : 'Add lender / borrower'}
            </button>
          </div>

          <div className='flex-1 overflow-y-auto flex flex-col min-h-0'>
            <div className='px-3 py-2 flex items-center justify-between'>
              <span className='text-xs font-medium text-gray-500 uppercase tracking-wide'>
                Your conversations
              </span>
              {savedSessions.length > 0 && (
                <button
                  type='button'
                  onClick={handleClearAllSessions}
                  className='text-xs text-[#7c3aed] hover:underline'
                >
                  Clear All
                </button>
              )}
            </div>
            <ul className='px-2 pb-4 space-y-0.5'>
              {savedSessions.length === 0 ? (
                <li className='px-3 py-4 text-sm text-gray-400 text-center'>
                  No sessions yet. Start a chat and save it.
                </li>
              ) : (
                savedSessions.map((s) => (
                  <li key={s.id}>
                    <button
                      type='button'
                      onClick={() => handleOpenSession(s.id)}
                      className={`w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-left transition-colors group ${
                        activeSessionId === s.id
                          ? 'bg-[#ede9fe] text-[#5b21b6]'
                          : 'hover:bg-gray-100 text-gray-700'
                      }`}
                    >
                      <span className='shrink-0 w-6 h-6 rounded bg-gray-200 flex items-center justify-center text-gray-500 text-xs'>
                        💬
                      </span>
                      <span className='min-w-0 flex-1 text-sm truncate font-medium'>
                        {s.name}
                      </span>
                      <button
                        type='button'
                        onClick={(e) => handleDeleteSession(e, s.id)}
                        className='shrink-0 p-1 rounded text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity'
                        title='Delete'
                        aria-label='Delete session'
                      >
                        ×
                      </button>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className='p-3 border-t border-gray-100 space-y-2'>
            {saveFeedback && (
              <p className='text-xs text-emerald-600 px-1'>{saveFeedback}</p>
            )}
            <button
              type='button'
              onClick={() => {
                handleSaveSession();
                setSidebarOpen(false);
              }}
              className='w-full rounded-xl py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 border border-gray-200 transition-colors'
            >
              Save session
            </button>
            <div className='relative' ref={languageRef}>
              <button
                type='button'
                onClick={() => setLanguageDropdownOpen((o) => !o)}
                className='w-full rounded-xl py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 border border-gray-200 flex items-center justify-between px-3'
              >
                <span>
                  🌐{' '}
                  {LANGUAGE_OPTIONS.find((o) => o.value === languagePref)
                    ?.label ?? languagePref}
                </span>
                <span className='text-gray-400'>
                  {languageDropdownOpen ? '▲' : '▼'}
                </span>
              </button>
              {languageDropdownOpen && (
                <ul className='absolute bottom-full left-0 right-0 mb-1 rounded-xl border border-gray-200 bg-white shadow-lg py-1 z-10'>
                  {LANGUAGE_OPTIONS.map((opt) => (
                    <li
                      key={opt.value}
                      role='option'
                      onClick={() => {
                        setLanguagePref(opt.value);
                        setLanguageDropdownOpen(false);
                      }}
                      className={`px-3 py-2 text-sm cursor-pointer ${
                        languagePref === opt.value
                          ? 'bg-[#ede9fe] text-[#5b21b6] font-medium'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      {opt.label}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </aside>

        {/* Main area: chat or admin */}
        <main className='flex-1 flex flex-col min-w-0 min-h-0 p-1 sm:p-2 md:p-3'>
          {viewMode === 'admin' ? (
            <AdminPanel apiUrl={API_URL} />
          ) : !hasWa ? (
            <div className='flex-1 flex flex-col bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-100 overflow-hidden min-h-0 items-center justify-center p-6'>
              <div className='w-full max-w-sm space-y-4'>
                <h2 className='text-lg font-semibold text-gray-900 text-center'>
                  Enter your WhatsApp number
                </h2>
                <p className='text-sm text-gray-500 text-center'>
                  This links your chat to your WhatsApp so we can keep your
                  conversation in sync. Use the same number you use on WhatsApp
                  (e.g. +27…).
                </p>
                <form onSubmit={handlePreChatSubmit} className='space-y-3'>
                  <input
                    type='tel'
                    value={preChatWaInput}
                    onChange={(e) => {
                      setPreChatWaInput(e.target.value);
                      setPreChatError(null);
                    }}
                    placeholder='e.g. +27603116777'
                    className='w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-[#7c3aed] focus:outline-none focus:ring-2 focus:ring-[#ede9fe]'
                    aria-label='WhatsApp number'
                  />
                  {preChatError && (
                    <p className='text-sm text-red-600' role='alert'>
                      {preChatError}
                    </p>
                  )}
                  <button
                    type='submit'
                    disabled={!preChatWaInput.trim()}
                    className='w-full rounded-xl bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 text-sm transition-colors'
                  >
                    Continue to chat
                  </button>
                </form>
              </div>
            </div>
          ) : (
            <div className='flex-1 flex flex-col bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-100 overflow-hidden min-h-0'>
              <div className='px-3 sm:px-5 py-3 border-b border-gray-100 space-y-2 shrink-0'>
                <div className='flex items-center gap-2'>
                  <button
                    type='button'
                    aria-label='Open menu'
                    className='md:hidden p-2 -ml-1 rounded-lg text-gray-600 hover:bg-gray-100'
                    onClick={() => setSidebarOpen(true)}
                  >
                    <svg
                      className='w-5 h-5'
                      fill='none'
                      stroke='currentColor'
                      viewBox='0 0 24 24'
                      aria-hidden
                    >
                      <path
                        strokeLinecap='round'
                        strokeLinejoin='round'
                        strokeWidth={2}
                        d='M4 6h16M4 12h16M4 18h16'
                      />
                    </svg>
                  </button>
                  <h2 className='flex-1 min-w-0 text-sm font-medium text-gray-500 truncate'>
                    {getConversationTitle(messages)}
                  </h2>
                  <div className='flex items-center gap-1 sm:gap-2 shrink-0'>
                    <button
                      type='button'
                      onClick={handleNewSession}
                      className='flex items-center gap-1 rounded-lg border border-violet-200 bg-violet-50 px-2.5 py-1.5 text-xs font-medium text-violet-700 hover:bg-violet-100 hover:border-violet-300 transition-colors'
                      title='New chat'
                    >
                      <svg
                        className='w-3.5 h-3.5'
                        fill='none'
                        stroke='currentColor'
                        viewBox='0 0 24 24'
                        aria-hidden
                      >
                        <path
                          strokeLinecap='round'
                          strokeLinejoin='round'
                          strokeWidth={2}
                          d='M12 4v16m8-8H4'
                        />
                      </svg>
                      New
                    </button>
                    <button
                      type='button'
                      onClick={handleSaveSession}
                      className='flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors'
                      title='Save this chat'
                    >
                      <svg
                        className='w-3.5 h-3.5'
                        fill='none'
                        stroke='currentColor'
                        viewBox='0 0 24 24'
                        aria-hidden
                      >
                        <path
                          strokeLinecap='round'
                          strokeLinejoin='round'
                          strokeWidth={2}
                          d='M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4'
                        />
                      </svg>
                      Save
                    </button>
                    <button
                      type='button'
                      onClick={() => setSidebarOpen(true)}
                      className='flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors'
                      title='Load saved chat'
                    >
                      <svg
                        className='w-3.5 h-3.5'
                        fill='none'
                        stroke='currentColor'
                        viewBox='0 0 24 24'
                        aria-hidden
                      >
                        <path
                          strokeLinecap='round'
                          strokeLinejoin='round'
                          strokeWidth={2}
                          d='M5 19a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v2a2 2 0 01-2 2h-2m-4 0h2a2 2 0 002-2V9a2 2 0 00-2-2h-2a2 2 0 00-2 2v2a2 2 0 002 2zm0 0h2a2 2 0 002-2v-2a2 2 0 00-2-2h-2a2 2 0 00-2 2v2a2 2 0 002 2z'
                        />
                      </svg>
                      Load
                    </button>
                  </div>
                </div>
              </div>

              <div
                ref={listRef}
                className='flex-1 overflow-y-auto overflow-x-hidden p-3 sm:p-5 space-y-4 sm:space-y-6 min-h-0 max-h-[calc(100dvh-11rem)]'
              >
                {messages.map((msg, i) => (
                  <div key={i} className='space-y-1'>
                    <ChatMessage
                      role={msg.role}
                      content={msg.content}
                      responseTimeMs={msg.responseTimeMs}
                      quickActions={QUICK_ACTIONS}
                      adminQuickActions={
                        isAdminUser(waNumber) ? ADMIN_QUICK_ACTIONS : undefined
                      }
                      onQuickAction={handleQuickAction}
                      onRetry={
                        msg.role === 'user'
                          ? () => handleSend(msg.content)
                          : undefined
                      }
                    />
                    {msg.role === 'assistant' &&
                      msg.interactive &&
                      msg.interactive.options?.length > 0 && (
                        <div className='pl-0'>
                          <InteractiveBlock
                            spec={msg.interactive}
                            onSelect={handleSend}
                            disabled={isLoading}
                          />
                        </div>
                      )}
                  </div>
                ))}
                {isLoading && <TypingIndicator />}
              </div>

              <div className='border-t border-gray-100 p-3 sm:p-4 shrink-0'>
                <ChatInput
                  onSend={handleSend}
                  disabled={isLoading}
                  placeholder="What's on your mind?"
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
