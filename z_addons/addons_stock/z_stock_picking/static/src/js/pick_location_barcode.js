/** @odoo-module **/

import {FormController} from "@web/views/form/form_controller"
import {Dialog} from "@web/core/dialog/dialog"
import {useChildRef, useService} from "@web/core/utils/hooks"
import {Component, onWillUnmount, EventBus} from "@odoo/owl"
import {_t} from "@web/core/l10n/translation"
import {isBarcodeScannerSupported, scanBarcode} from "@web/webclient/barcode/barcode_scanner"


export class FormPickLocationRender extends FormController {
    setup() {
        this.bus = new EventBus()
        this.modalRef = useChildRef()
        this.isProcess = false
        this.dialog = useService("dialog")
        this.notificationService = useService("notification")
        this.actionService = useService("action")
        super.setup()
    }

    async pickLocationBarcodeDialog() {
        var self = this
        var model = this.props.resModel
        let error = null
        const constraints = {
            video: {facingMode: this.props.facingMode}, audio: false,
        }
        try {
            let barcode = await scanBarcode(this.env, this.facingMode)
            let pick_location_id = this.model.config.resId
            let data = await this.orm.call('stock.picking', 'barcode_product_search', [barcode, pick_location_id])
            if (data[0] === 'package') {
                this.actionService.doAction({
                    name: _t('Location Pick'),
                    type: 'ir.actions.act_window',
                    res_model: 'stock.move.location.pick',
                    views: [[false, "form"]],
                    view_mode: "form",
                    target: 'new',
                    res_id: pick_location_id,
                })
            } else if (data[0] === 'product') {
                this.actionService.doAction({
                    name: _t('Package Pick'),
                    type: 'ir.actions.act_window',
                    res_model: 'stock.quant.package.pick',
                    views: [[false, "form"]],
                    view_mode: "form",
                    target: 'new',
                    res_id: data[1],
                })
            }
        } catch (err) {
            error = err.message
            alert(error)
        }
    }
}

FormPickLocationRender.template = 'pick_location.barcode_scanner'
