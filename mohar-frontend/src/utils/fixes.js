// Safe helpers for applying a suggested fix to the editor text.

// A fix can only be applied if the flagged text is still in the editor.
export const canApplyFix = (text, excerpt) => Boolean(excerpt) && text.includes(excerpt);

// Replaces the FIRST occurrence. Uses a function so "$&"-style text is never misread.
export const applyFixToText = (text, excerpt, fix) => text.replace(excerpt, () => fix);
