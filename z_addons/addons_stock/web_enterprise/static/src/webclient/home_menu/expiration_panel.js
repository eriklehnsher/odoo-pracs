/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Transition } from "@web/core/transition";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, useRef } from "@odoo/owl";


export class ExpirationPanel extends Component {
    setup() {
        this.subscription = useState(useService("enterprise_subscription"));

        this.state = useState({
            displayRegisterForm: false,
        });

        this.inputRef = useRef("input");
    }

    get buttonText() {
        return this.subscription.lastRequestStatus === "error" ? _t("Retry") : _t("Register");
    }

    get alertType() {
        return "info";
    }

    get expirationMessage() {
        return _t("");
    }

    showRegistrationForm() {
        this.state.displayRegisterForm = !this.state.displayRegisterForm;
    }

    async onCodeSubmit() {
        return;
    }
}

ExpirationPanel.template = "DatabaseExpirationPanel";
ExpirationPanel.props = {};
ExpirationPanel.components = { Transition };
