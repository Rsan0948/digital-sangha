import tsParser from '@typescript-eslint/parser';
import svelteParser from 'svelte-eslint-parser';
import sveltePlugin from 'eslint-plugin-svelte';

export default [
  {
    ignores: [
      'dist/',
      'node_modules/',
      'public/',
      'tests-e2e/',
      'svelte.config.js',
      'vite.config.ts',
      'vite.config.ts.timestamp-*.mjs',
      'eslint.config.js',
      'playwright.config.ts',
    ],
  },
  {
    files: ['**/*.ts'],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 'latest',
      sourceType: 'module',
    },
    rules: {
      'no-debugger': 'error',
    },
  },
  {
    files: ['**/*.svelte'],
    plugins: { svelte: sveltePlugin },
    languageOptions: {
      parser: svelteParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    rules: {},
  },
];
