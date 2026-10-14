import { Component, type ReactNode } from "react";

// Keeps one broken panel from blanking the whole dashboard.
export default class ErrorBoundary extends Component<{ children: ReactNode; label?: string }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="banner inline" onClick={() => this.setState({ error: null })}>
        {this.props.label ?? "This panel"} hit a display error: {this.state.error.message}. Click to retry.
      </div>
    );
  }
}
