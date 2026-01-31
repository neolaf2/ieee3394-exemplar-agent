declare module 'qrcode-terminal' {
  export function generate(input: string, opts?: { small?: boolean }): void;
  export function setErrorLevel(level: 'L' | 'M' | 'Q' | 'H'): void;
}
