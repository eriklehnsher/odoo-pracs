/** @odoo-module **/

import BarcodeQuantModel from '@stock_barcode/models/barcode_quant_model'
import {patch} from "@web/core/utils/patch"
import {_t} from "@web/core/l10n/translation"

patch(BarcodeQuantModel.prototype, {

    // constructor(params) {
    //     this.super(...arguments)
    //     this.lastScanned = {packageId: false, product: false, sourceLocation: false, warehouse: false}
    //     this.lastScanned1 = {warehouse: false}
    // },

    get warehouse() {
        if (this.lastScanned.warehouse) {
            return this.cache.getRecord('stock.warehouse', this.lastScanned.warehouse.id)
        }
        return false
    },

    set warehouse(warehouse) {
        this._currentWarehouse = warehouse
        this.lastScanned.warehouse = warehouse
    },

    get barcodeInfo() {
        debugger
        // Takes the parent line if the current line is part of a group.
        let line = this._getParentLine(this.selectedLine) || this.selectedLine;
        if (!line && this.lastScanned.packageId) {
            line = this.pageLines.find(l => l.package_id && l.package_id.id === this.lastScanned.packageId);
        }
        // Defines some messages who can appear in multiple cases.
        const messages = {
            scanProduct: {
                class: 'scan_product', message: _t("Scan a product"), icon: 'tags',
            }, scanLot: {
                class: 'scan_lot',
                message: _t("Scan lot numbers for product %s to change their quantity", line ? line.product_id.display_name : ""),
                icon: 'barcode',
            }, scanSerial: {
                class: 'scan_serial',
                message: _t("Scan serial numbers for product %s to change their quantity", line ? line.product_id.display_name : ""),
                icon: 'barcode',
            },
        };

        if (line && this.lastScanned.warehouse && this.lastScanned.sourceLocation) { // Message depends of the selected line's state.
            const {tracking} = line.product_id;
            const trackingNumber = (line.lot_id && line.lot_id.name) || line.lot_name;
            if (this._lineIsNotComplete(line)) {
                if (tracking !== 'none') {
                    return tracking === 'lot' ? messages.scanLot : messages.scanSerial;
                }
                return messages.scanProduct;
            } else if (tracking !== 'none' && !trackingNumber) {
                // Line's quantity is fulfilled but still waiting a tracking number.
                return tracking === 'lot' ? messages.scanLot : messages.scanSerial;
            } else { // Line's quantity is fulfilled.
                if (this.groups.group_stock_multi_locations && line.location_id.id === this.location.id) {
                    return {
                        class: 'scan_product_or_src',
                        message: _t("Scan more products in %s or scan another location", this.location.display_name),
                    };
                }
                return messages.scanProduct;
            }
        }

        if (!this.lastScanned.warehouse && !this.lastScanned.sourceLocation) {
            return {
                class: 'scan_warehouse', message: _t('Scan a warehouse or a location'), icon: 'sign-out',
            }
        }

        // No line selected, returns default message (depends if multilocation is enabled).
        if (this.groups.group_stock_multi_locations) {
            if (!this.lastScanned.sourceLocation) {
                return {
                    class: 'scan_src', message: _t("Scan a location"), icon: 'sign-out',
                };
            }
            return {
                class: 'scan_product_or_src',
                message: _t("Scan a product in %s or scan another location", this.location.display_name),
            };
        }
        return messages.scanProduct;
    },

    setData(data) {
        super.setData(...arguments)
    },

    async _processBarcode(barcode) {
        let barcodeData = {};
        let currentLine = false;
        // Creates a filter if needed, which can help to get the right record
        // when multiple records have the same model and barcode.
        const filters = {};
        if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
            filters['stock.lot'] = {
                product_id: this.selectedLine.product_id.id,
            };
        }
        // Constrain DB reads to records which belong to the company defined on the open operation
        filters['all'] = {
            company_id: [false].concat(this._getCompanyId() || []),
        };
        try {
            barcodeData = await this._parseBarcode(barcode, filters);
            if (this._shouldSearchForAnotherLot(barcodeData, filters)) {
                // Retry to parse the barcode without filters in case it matches an existing
                // record that can't be found because of the filters
                const lot = await this.cache.getRecordByBarcode(barcode, 'stock.lot');
                if (lot) {
                    Object.assign(barcodeData, {lot, match: true});
                }
            }
        } catch (parseErrorMessage) {
            barcodeData.error = parseErrorMessage;
        }

        // Keep in memory every scans.
        this.scanHistory.unshift(barcodeData);

        if (barcodeData.match) { // Makes flash the screen if the scanned barcode was recognized.
            this.trigger('flash');
        }

        // Process each data in order, starting with non-ambiguous data type.
        if (barcodeData.action) { // As action is always a single data, call it and do nothing else.
            return await barcodeData.action();
        }

        if (barcodeData.packaging) {
            Object.assign(barcodeData, this._retrievePackagingData(barcodeData));
        }

        // Depending of the configuration, the user can be forced to scan a specific barcode type.
        const check = this._checkBarcode(barcodeData);
        if (check.error) {
            return this.notification(check.message, {title: check.title, type: "danger"});
        }

        if (barcodeData.product) { // Remembers the product if a (packaging) product was scanned.
            this.lastScanned.product = barcodeData.product;
        }

        if (barcodeData.lot && !barcodeData.product) {
            Object.assign(barcodeData, this._retrieveTrackingNumberInfo(barcodeData.lot));
        }

        // bach2tn custom _processWarehouse
        await this._processWarehouse(barcodeData)
        await this._processLocation(barcodeData);
        await this._processPackage(barcodeData);
        if (barcodeData.stopped) {
            // TODO: Sometime we want to stop here instead of keeping doing thing,
            // but it's a little hacky, it could be better to don't have to do that.
            return;
        }

        if (barcodeData.weight) { // Convert the weight into quantity.
            barcodeData.quantity = barcodeData.weight.value;
        }

        // If no product found, take the one from last scanned line if possible.
        if (!barcodeData.product) {
            if (barcodeData.quantity) {
                currentLine = this.selectedLine || this.lastScannedLine;
            } else if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
                currentLine = this.selectedLine;
            } else if (this.lastScannedLine && this.lastScannedLine.product_id.tracking !== 'none') {
                currentLine = this.lastScannedLine;
            }
            if (currentLine) { // If we can, get the product from the previous line.
                const previousProduct = currentLine.product_id;
                // If the current product is tracked and the barcode doesn't fit
                // anything else, we assume it's a new lot/serial number.
                if (previousProduct.tracking !== 'none' && !barcodeData.match && this.canCreateNewLot) {
                    this.trigger('flash');
                    barcodeData.lotName = barcode;
                    barcodeData.product = previousProduct;
                }
                if (barcodeData.lot || barcodeData.lotName || barcodeData.quantity) {
                    barcodeData.product = previousProduct;
                }
            }
        }
        let {product} = barcodeData;
        if (!product && barcodeData.match && this.parser.nomenclature.is_gs1_nomenclature) {
            // Special case where something was found using the GS1 nomenclature but no product is
            // used (eg.: a product's barcode can be read as a lot is starting with 21).
            // In such case, tries to find a record with the barcode by by-passing the parser.
            barcodeData = await this._fetchRecordFromTheCache(barcode, filters);
            if (barcodeData.packaging) {
                Object.assign(barcodeData, this._retrievePackagingData(barcodeData));
            } else if (barcodeData.lot) {
                Object.assign(barcodeData, this._retrieveTrackingNumberInfo(barcodeData.lot));
            }
            if (barcodeData.product) {
                product = barcodeData.product;
            } else if (barcodeData.match) {
                await this._processPackage(barcodeData);
                if (barcodeData.stopped) {
                    return;
                }
            }
        }
        if (!product) { // Product is mandatory, if no product, raises a warning.
            if (!barcodeData.error) {
                if (this.groups.group_tracking_lot) {
                    barcodeData.error = _t("You are expected to scan one or more products or a package available at the picking location");
                } else {
                    barcodeData.error = _t("You are expected to scan one or more products.");
                }
            }
            return this.notification(barcodeData.error, {type: "danger"});
        } else if (barcodeData.lot && barcodeData.lot.product_id !== product.id) {
            delete barcodeData.lot; // The product was scanned alongside another product's lot.
        }
        if (barcodeData.weight) { // the encoded weight is based on the product's UoM
            barcodeData.uom = this.cache.getRecord('uom.uom', product.uom_id);
        }

        // Searches and selects a line if needed.
        if (!currentLine || this._shouldSearchForAnotherLine(currentLine, barcodeData)) {
            currentLine = this._findLine(barcodeData);
        }

        // Default quantity set to 1 by default if the product is untracked or
        // if there is a scanned tracking number.
        if (product.tracking === 'none' || barcodeData.lot || barcodeData.lotName || this._incrementTrackedLine()) {
            const hasUnassignedQty = currentLine && currentLine.qty_done && !currentLine.lot_id && !currentLine.lot_name;
            const isTrackingNumber = barcodeData.lot || barcodeData.lotName;
            const defaultQuantity = isTrackingNumber && hasUnassignedQty ? 0 : 1;
            barcodeData.quantity = barcodeData.quantity || defaultQuantity;
            if (product.tracking === 'serial' && barcodeData.quantity > 1 && (barcodeData.lot || barcodeData.lotName)) {
                barcodeData.quantity = 1;
                this.notification(_t(`A product tracked by serial numbers can't have multiple quantities for the same serial number.`), {type: 'danger'});
            }
        }

        if ((barcodeData.lotName || barcodeData.lot) && product) {
            const lotName = barcodeData.lotName || barcodeData.lot.name;
            for (const line of this.currentState.lines) {
                if (line.product_id.tracking === 'serial' && this.getQtyDone(line) !== 0 && ((line.lot_id && line.lot_id.name) || line.lot_name) === lotName) {
                    return this.notification(_t("The scanned serial number is already used."), {type: 'danger'});
                }
            }
            // Prefills `owner_id` and `package_id` if possible.
            const prefilledOwner = (!currentLine || (currentLine && !currentLine.owner_id)) && this.groups.group_tracking_owner && !barcodeData.owner;
            const prefilledPackage = (!currentLine || (currentLine && !currentLine.package_id)) && this.groups.group_tracking_lot && !barcodeData.package;
            if (this.useExistingLots && (prefilledOwner || prefilledPackage)) {
                const lotId = (barcodeData.lot && barcodeData.lot.id) || (currentLine && currentLine.lot_id && currentLine.lot_id.id) || false;
                const res = await this.orm.call('product.product', 'prefilled_owner_package_stock_barcode', [product.id], {
                    lot_id: lotId,
                    lot_name: (!lotId && barcodeData.lotName) || false,
                    context: {location_id: currentLine.location_id},
                },);
                this.cache.setCache(res.records);
                if (prefilledPackage && res.quant && res.quant.package_id) {
                    barcodeData.package = this.cache.getRecord('stock.quant.package', res.quant.package_id);
                }
                if (prefilledOwner && res.quant && res.quant.owner_id) {
                    barcodeData.owner = this.cache.getRecord('res.partner', res.quant.owner_id);
                }
            }
        }

        // Updates or creates a line based on barcode data.
        if (currentLine) { // If line found, can it be incremented ?
            let exceedingQuantity = 0;
            if (product.tracking !== 'serial' && barcodeData.uom && barcodeData.uom.category_id == currentLine.product_uom_id.category_id) {
                // convert to current line's uom
                barcodeData.quantity = (barcodeData.quantity / barcodeData.uom.factor) * currentLine.product_uom_id.factor;
                barcodeData.uom = currentLine.product_uom_id;
            }
            // Checks the quantity doesn't exceed the line's remaining quantity.
            if (currentLine.reserved_uom_qty && product.tracking === 'none') {
                const remainingQty = currentLine.reserved_uom_qty - currentLine.qty_done;
                if (barcodeData.quantity > remainingQty && this._shouldCreateLineOnExceed(currentLine)) {
                    // In this case, lowers the increment quantity and keeps
                    // the excess quantity to create a new line.
                    exceedingQuantity = barcodeData.quantity - remainingQty;
                    barcodeData.quantity = remainingQty;
                }
            }
            if (barcodeData.quantity > 0 || barcodeData.lot || barcodeData.lotName) {
                const fieldsParams = this._convertDataToFieldsParams(barcodeData);
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                await this.updateLine(currentLine, fieldsParams);
            }
            if (exceedingQuantity) { // Creates a new line for the excess quantity.
                barcodeData.quantity = exceedingQuantity;
                const fieldsParams = this._convertDataToFieldsParams(barcodeData);
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                currentLine = await this._createNewLine({
                    copyOf: currentLine, fieldsParams,
                });
            }
        } else { // No line found, so creates a new one.
            const fieldsParams = this._convertDataToFieldsParams(barcodeData);
            if (barcodeData.uom) {
                fieldsParams.uom = barcodeData.uom;
            }
            if (this.lastScanned.warehouse && this.lastScanned.sourceLocation)
                currentLine = await this.createNewLine({fieldsParams});
        }

        // And finally, if the scanned barcode modified a line, selects this line.
        if (currentLine) {
            this._selectLine(currentLine);
        }
        this.trigger('update');
    },

    async _processWarehouse(barcodeData) {
        if (barcodeData.warehouse) {
            await this.__processWarehouse(barcodeData)
            this.trigger('update')
        }


    },

    async __processWarehouse(barcodeData) {
        this.warehouse = barcodeData.warehouse
        barcodeData.stopped = true
        this.selectedLineVirtualId = false
    },


    async _fetchRecordFromTheCache(barcode, filters, data) {
        debugger
        const result = data || {barcode, match: false};
        const recordByData = await this.cache.getRecordByBarcode(barcode, false, false, filters);
        if (recordByData.size > 1) {
            const message = _t("Barcode scan is ambiguous with several model: %s. Use the most likely.", Array.from(recordByData.keys()));
            this.notification(message, {type: "warning"});
        }

        if (this.groups.group_stock_multi_locations) {
            debugger
            const location = recordByData.get('stock.location');
            if (location) {
                this._setLocationFromBarcode(result, location);
                result.match = true
                debugger
                let _idd = location['id']
                const warehouse_obj = await this.orm.call('stock.location', 'get_warehouse_by_location', [[_idd]])
                debugger
                if (warehouse_obj) {
                    result.warehouse = warehouse_obj
                    result.match = true
                } else {
                    const message = _t("The location corresponding to the barcode you just scanned does not belong to any warehouse.", Array.from(recordByData.keys()))
                    this.notification(message, {type: 'danger'})
                }
            } else {
                // Custom for stock.warehouse
                const warehouse = recordByData.get('stock.warehouse')
                if (warehouse) {
                    result.warehouse = warehouse
                    result.match = true
                }
            }

        }

        if (this.groups.group_tracking_lot) {
            const packageType = recordByData.get('stock.package.type');
            const stockPackage = recordByData.get('stock.quant.package');
            if (stockPackage) {
                // TODO: should take packages only in current (sub)location.
                result.package = stockPackage;
                result.match = true;
            }
            if (packageType) {
                result.packageType = packageType;
                result.match = true;
            }
        }

        const product = recordByData.get('product.product');
        if (product) {
            result.product = product;
            result.match = true;
        }
        if (this.groups.group_stock_packaging) {
            const packaging = recordByData.get('product.packaging');
            if (packaging) {
                result.match = true;
                result.packaging = packaging;
            }
        }
        if (this.useExistingLots) {
            const lot = recordByData.get('stock.lot');
            if (lot) {
                result.lot = lot;
                result.match = true;
            }
        }


        if (!result.match && this.packageTypes.length) {
            // If no match, check if the barcode begins with a package type's barcode.
            for (const [packageTypeBarcode, packageTypeId] of this.packageTypes) {
                if (barcode.indexOf(packageTypeBarcode) === 0) {
                    result.packageType = await this.cache.getRecord('stock.package.type', packageTypeId);
                    result.packageName = barcode;
                    result.match = true;
                    break;
                }
            }
        }
        return result
    },

    _createLinesState() {
        debugger
        const today = new Date().toISOString().slice(0, 10);
        const lines = [];
        for (const id of Object.keys(this.cache.dbIdCache['stock.quant']).map(id => Number(id))) {
            const quant = this.cache.getRecord('stock.quant', id);
            if (quant.user_id !== this.userId || quant.inventory_date > today) {
                // Doesn't take quants who must be counted by another user or in the future.
                continue;
            }
            // Checks if this line is already in the quant state to get back
            // its `virtual_id` (and so, avoid to set a new `virtual_id`).
            const prevLine = this.currentState && this.currentState.lines.find(l => l.id === id);
            const previousVirtualId = prevLine && prevLine.virtual_id;
            quant.dummy_id = quant.dummy_id && Number(quant.dummy_id);
            quant.virtual_id = quant.dummy_id || previousVirtualId || this._uniqueVirtualId;
            quant.product_id = this.cache.getRecord('product.product', quant.product_id);
            quant.location_id = this.cache.getRecord('stock.location', quant.location_id);
            quant.lot_id = quant.lot_id && this.cache.getRecord('stock.lot', quant.lot_id);
            quant.package_id = quant.package_id && this.cache.getRecord('stock.quant.package', quant.package_id);
            quant.owner_id = quant.owner_id && this.cache.getRecord('res.partner', quant.owner_id);
            quant.warehouse_id = quant.warehouse_id && this.cache.getRecord('stock.warehouse', quant.warehouse_id)
            lines.push(Object.assign({}, quant));
        }
        debugger
        return lines;
    },

    _getFieldToWrite() {
        return [
            'inventory_date',
            'inventory_quantity',
            'inventory_quantity_set',
            'user_id',
            'location_id',
            'lot_name',
            'lot_id',
            'package_id',
            'owner_id',
            'warehouse_id',
        ];
    },


})
