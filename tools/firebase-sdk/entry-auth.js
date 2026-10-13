// Google sign-in. Rebuild with: npm install && npm run build
export { initializeApp } from "firebase/app";
export {
  initializeAuth, inMemoryPersistence, browserPopupRedirectResolver,
  GoogleAuthProvider, signInWithPopup, signOut,
} from "firebase/auth";
