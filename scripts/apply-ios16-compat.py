#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
if (ROOT / "ios").exists():
    repo = ROOT
else:
    repo = Path.cwd()
sources = repo / "ios/MimiRemote/Sources"


def replace_balanced_call(text: str, method: str, replacement: str) -> str:
    needle = f".{method}("
    pos = 0
    out: list[str] = []
    while True:
        start = text.find(needle, pos)
        if start < 0:
            out.append(text[pos:])
            break
        out.append(text[pos:start])
        i = start + len(needle)
        depth = 1
        in_string = False
        escape = False
        while i < len(text) and depth:
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
            i += 1
        if depth != 0:
            raise RuntimeError(f"unbalanced call for {method} near offset {start}")
        out.append(replacement)
        pos = i
    return "".join(out)


def patch_text(text: str) -> str:
    text = text.replace("ContentUnavailableView", "MimiContentUnavailableView")
    text = text.replace(".onChange(of:", ".mimiOnChange(of:")
    text = text.replace(".onScrollGeometryChange", ".mimiOnScrollGeometryChange")
    text = text.replace(".onScrollPhaseChange", ".mimiOnScrollPhaseChange")
    text = text.replace(".onScrollVisibilityChange", ".mimiOnScrollVisibilityChange")
    text = text.replace(".scrollPosition(", ".mimiScrollPosition(")
    text = text.replace(".scrollTransition(", ".mimiScrollTransition(")
    text = text.replace(".onKeyPress(", ".mimiOnKeyPress(")
    text = re.sub(r"\bScrollPosition\b", "MimiScrollPosition", text)
    text = re.sub(r"\bScrollGeometry\b", "MimiScrollGeometry", text)
    text = re.sub(r"\bScrollPhase\b", "MimiScrollPhase", text)
    text = re.sub(r"\bKeyPress\b", "MimiKeyPress", text)
    text = text.replace(".inspector(isPresented:", ".mimiInspector(isPresented:")

    for method in (
        "presentationSizing",
        "listSectionSpacing",
        "contentMargins",
        "defaultScrollAnchor",
        "navigationTransition",
        "matchedTransitionSource",
        "toolbarBackgroundVisibility",
        "inspectorColumnWidth",
        "symbolEffect",
        "containerRelativeFrame",
        "scrollTargetLayout",
        "scrollTargetBehavior",
        "focusable",
    ):
        text = replace_balanced_call(text, method, ".mimiLegacyNoop()")

    text = text.replace(
        "            contentMargins(.top, 0, for: .scrollContent)",
        "            self",
    )

    modern_animation = '''        withAnimation(\n            MimiMotion.gestureSettling.animation(\n                reduceMotion: reduceMotion,\n                initialVelocity: settling.springInitialVelocity\n            ),\n            completionCriteria: .logicallyComplete\n        ) {\n            floatingSidebarPresentation.startSettling(settling)\n        } completion: {\n            guard floatingSidebarPresentation.completeSettling(\n                revision: settling.revision\n            ) else {\n                return\n            }\n            floatingSidebarRenderedProgress.record(settling.target.progress)\n            MimiHaptics.fire(.snap)\n        }'''
    legacy_animation = '''        withAnimation(\n            MimiMotion.gestureSettling.animation(\n                reduceMotion: reduceMotion,\n                initialVelocity: settling.springInitialVelocity\n            )\n        ) {\n            floatingSidebarPresentation.startSettling(settling)\n        }\n        guard floatingSidebarPresentation.completeSettling(\n            revision: settling.revision\n        ) else {\n            return\n        }\n        floatingSidebarRenderedProgress.record(settling.target.progress)\n        MimiHaptics.fire(.snap)'''
    text = text.replace(modern_animation, legacy_animation)

    text = text.replace(
        '''tokens.secondaryText.mix(\n                            with: tokens.primaryText,\n                            by: Double(progress)\n                        )''',
        "(progress >= 0.5 ? tokens.primaryText : tokens.secondaryText)",
    )
    return text


for path in sources.rglob("*.swift"):
    original = path.read_text()
    patched = patch_text(original)
    if patched != original:
        path.write_text(patched)

root_view = sources / "RootView.swift"
text = root_view.read_text()
marker = "// MARK: - iOS 16.5 personal compatibility layer"
if marker not in text:
    text += r'''

// MARK: - iOS 16.5 personal compatibility layer

private struct MimiOnChangeModifier<Value: Equatable>: ViewModifier {
    let value: Value
    let initial: Bool
    let action: (Value, Value) -> Void
    @State private var previousValue: Value?
    @State private var appeared = false

    func body(content: Content) -> some View {
        content
            .onAppear {
                if !appeared {
                    appeared = true
                    previousValue = value
                    if initial {
                        action(value, value)
                    }
                }
            }
            .onChange(of: value) { newValue in
                let oldValue = previousValue ?? newValue
                previousValue = newValue
                action(oldValue, newValue)
            }
    }
}

struct MimiContentUnavailableView: View {
    private let content: AnyView

    init(_ title: String, systemImage: String, description: Text? = nil) {
        content = AnyView(
            VStack(spacing: 12) {
                Image(systemName: systemImage)
                    .font(.title2)
                Text(title)
                    .font(.headline)
                    .multilineTextAlignment(.center)
                if let description {
                    description
                        .font(.subheadline)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.secondary)
                }
            }
            .padding()
        )
    }

    init<Label: View, Description: View>(
        @ViewBuilder label: () -> Label,
        @ViewBuilder description: () -> Description
    ) {
        content = AnyView(
            VStack(spacing: 12) {
                label()
                    .font(.headline)
                description()
                    .font(.subheadline)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
            }
            .padding()
        )
    }

    init<Label: View, Description: View, Actions: View>(
        @ViewBuilder label: () -> Label,
        @ViewBuilder description: () -> Description,
        @ViewBuilder actions: () -> Actions
    ) {
        content = AnyView(
            VStack(spacing: 12) {
                label()
                    .font(.headline)
                description()
                    .font(.subheadline)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                actions()
            }
            .padding()
        )
    }

    var body: some View { content }
}

enum MimiScrollPhase: Equatable {
    case idle
    case tracking
    case interacting
    case decelerating
    case animating
}

struct MimiScrollGeometry {
    var contentOffset: CGPoint = .zero
    var contentSize: CGSize = .zero
    var containerSize: CGSize = .zero
    var contentInsets: EdgeInsets = EdgeInsets()
    var visibleRect: CGRect = .zero
}

struct MimiScrollPosition: Equatable {
    init<T>(idType: T.Type) {}
}

enum MimiScrollTransitionConfiguration {
    case interactive
}

struct MimiScrollTransitionPhase {
    let isIdentity: Bool = true
}

enum MimiKeyEquivalent: Hashable {
    case upArrow
    case downArrow
    case `return`
}

struct MimiKeyPress {
    enum Result {
        case handled
        case ignored
    }

    let key: MimiKeyEquivalent
}

extension View {
    func mimiOnChange<Value: Equatable>(
        of value: Value,
        initial: Bool = false,
        _ action: @escaping (Value, Value) -> Void
    ) -> some View {
        modifier(MimiOnChangeModifier(value: value, initial: initial, action: action))
    }

    func mimiLegacyNoop() -> some View { self }

    func mimiInspector<Inspector: View>(
        isPresented: Binding<Bool>,
        @ViewBuilder content: @escaping () -> Inspector
    ) -> some View {
        sheet(isPresented: isPresented, content: content)
    }

    func mimiScrollPosition(_ position: Binding<MimiScrollPosition>) -> some View { self }

    func mimiScrollPosition<ID: Hashable>(
        id: Binding<ID?>,
        anchor: UnitPoint? = nil
    ) -> some View { self }

    func mimiOnScrollGeometryChange<Value: Equatable>(
        for type: Value.Type,
        of transform: @escaping (MimiScrollGeometry) -> Value,
        action: @escaping (Value, Value) -> Void
    ) -> some View { self }

    func mimiOnScrollPhaseChange(
        _ action: @escaping (MimiScrollPhase, MimiScrollPhase) -> Void
    ) -> some View {
        onAppear { action(.idle, .idle) }
    }

    func mimiOnScrollVisibilityChange(
        threshold: Double = 0.5,
        _ action: @escaping (Bool) -> Void
    ) -> some View {
        onAppear { action(true) }
    }

    func mimiScrollTransition<Transformed: View>(
        _ configuration: MimiScrollTransitionConfiguration,
        axis: Axis,
        @ViewBuilder transition: @escaping (Self, MimiScrollTransitionPhase) -> Transformed
    ) -> some View { self }

    func mimiOnKeyPress(
        keys: [MimiKeyEquivalent],
        action: @escaping (MimiKeyPress) -> MimiKeyPress.Result
    ) -> some View { self }
}
'''
    root_view.write_text(text)

print("Applied iOS 16.5 compatibility source transforms.")
