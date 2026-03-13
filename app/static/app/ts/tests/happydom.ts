import { GlobalRegistrator } from "@happy-dom/global-registrator";

// Expose window and document globally for TypeScript tests
GlobalRegistrator.register();

// Override location.origin
Object.defineProperty(window.location, "origin", {
    value: "http://localhost",
    writable: true,
});
