import { applySwitcheroo } from "../designApplication";
import { ColorSet, ComponentId } from "../dataModels";
import { ComponentBase, ComponentState } from "./componentBase";
import { getPositionerByName, PopupManager } from "../popupManager";
import { stopPropagation } from "../eventHandling";

export type PopupState = ComponentState & {
    _type_: "Popup-builtin";
    anchor?: ComponentId;
    content?: ComponentId;
    is_open?: boolean;
    color?: ColorSet | "none";
    corner_radius?: number | [number, number, number, number];
    position?:
        | "auto"
        | "left"
        | "top"
        | "right"
        | "bottom"
        | "center"
        | "fullscreen"
        | "dropdown";
    alignment?: number;
    gap?: number;
    modal: boolean;
    user_closeable: boolean;
};

export class PopupComponent extends ComponentBase {
    declare state: Required<PopupState>;

    private contentContainer: HTMLElement;

    private popupManager: PopupManager;

    createElement(): HTMLElement {
        let element = document.createElement("div");
        element.classList.add("rio-popup-anchor");

        this.contentContainer = document.createElement("div");
        this.contentContainer.classList.add(
            "rio-popup-animation-scale",
            "rio-popup-content"
        );

        // Initialize the popup manager. Many of these values will be
        // overwritten by the updateElement method.
        this.popupManager = new PopupManager(
            element,
            this.contentContainer,
            getPositionerByName("center", 0, 0.5)
        );

        // Prevent clicking through the popup
        ["click", "pointerdown", "pointerup", "pointermove"].forEach(
            (eventType) => {
                this.contentContainer.addEventListener(eventType, (event) => {
                    stopPropagation(event);
                });
            }
        );

        return element;
    }

    updateElement(
        deltaState: PopupState,
        latentComponents: Set<ComponentBase>
    ): void {
        super.updateElement(deltaState, latentComponents);

        // Update the children
        this.replaceOnlyChild(
            latentComponents,
            deltaState.anchor,
            this.element
        );

        this.replaceOnlyChild(
            latentComponents,
            deltaState.content,
            this.contentContainer
        );

        // Update the popup manager
        if (
            deltaState.position !== undefined ||
            deltaState.alignment !== undefined ||
            deltaState.gap !== undefined
        ) {
            this.popupManager.positioner = getPositionerByName(
                deltaState.position ?? this.state.position,
                deltaState.gap ?? this.state.gap,
                deltaState.alignment ?? this.state.alignment
            );
        }

        // Open / Close
        if (deltaState.is_open !== undefined) {
            this.popupManager.isOpen = deltaState.is_open;
        }

        // Colorize
        if (deltaState.color === "none") {
            applySwitcheroo(this.contentContainer, "keep");
            this.contentContainer.style.removeProperty("background-color");
            this.contentContainer.style.removeProperty("box-shadow");
        } else if (deltaState.color !== undefined) {
            applySwitcheroo(this.contentContainer, deltaState.color);
            this.contentContainer.style.backgroundColor = `var(--rio-local-bg)`;
            this.contentContainer.style.boxShadow = `0 0 1rem var(--rio-global-shadow-color)`;
        }

        // Update the corner radius
        if (deltaState.corner_radius !== undefined) {
            if (typeof deltaState.corner_radius === "number") {
                this.contentContainer.style.borderRadius = `${deltaState.corner_radius}rem`;
            } else {
                this.contentContainer.style.borderRadius = `${deltaState.corner_radius[0]}rem ${deltaState.corner_radius[1]}rem ${deltaState.corner_radius[2]}rem ${deltaState.corner_radius[3]}rem`;
            }
        }

        // Modal
        if (deltaState.modal !== undefined) {
            this.popupManager.modal = deltaState.modal;
        }

        // User closeable
        if (deltaState.user_closeable !== undefined) {
            this.popupManager.userCloseable = deltaState.user_closeable;
        }
    }

    onDestruction(): void {
        super.onDestruction();
        this.popupManager.destroy();
    }
}
