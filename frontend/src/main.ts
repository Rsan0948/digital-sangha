import App from './App.svelte';
import './app.css';

// Early global error logging — these run before App.svelte's onMount has a
// chance to attach its handlers, so we capture mount-time failures too.
// App.svelte attaches its own listeners on mount and is responsible for
// rendering the user-facing fallback UI.
window.addEventListener('error', (event) => {
  console.error('window.error:', event.error ?? event.message);
});
window.addEventListener('unhandledrejection', (event) => {
  console.error('window.unhandledrejection:', event.reason);
});

const target = document.getElementById('app');
if (!target) {
  throw new Error('Mount target #app not found in document');
}

const app = new App({ target });

export default app;
