const { DiscountModel } = require('../model')

let getDiscounts = async(req, res) => {
    await DiscountModel.find()
        .then(result => {
            return res.status(200).json({ success: true, data: result })
        })
        .catch(err => {
            return res.status(400).json({ success: false, error: err })
        })
}

let getDiscountbyId = async(req, res) => {
    await DiscountModel.findOne({ _id: req.params.id }, (err, discount) => {
        if (err) {
            return res.status(400).json({ success: false, error: err })
        }

        if (!discount) {
            return res
                .status(404)
                .json({ success: false, error: `discount not found` })
        }
        return res.status(200).json({ success: true, data: discount })
    }).catch(err => console.log(err))
}

let updateDiscount = async(req, res) => {
    DiscountModel.findOne({ _id: req.params.id }, (err, result) => {
        if (err) {
            return res.status(404).json({
                err,
                message: 'discount not found!',
            })
        }
        result.storename = req.body.storename
        result.discount_profit = req.body.discount_profit
        result.discount_code = req.body.discount_code
        result.expireDatetime = req.body.expireDatetime
        result.apply = req.body.apply
        result
            .save()
            .then(() => {
                return res.status(200).json({
                    success: true,
                    message: 'discount updated!',
                    data: result
                })
            })
            .catch(error => {
                return res.status(404).json({
                    error,
                    message: 'discount not updated!',
                })
            })
    })
}
let deleteDiscount = async(req, res) => {
    await DiscountModel.findOneAndDelete({ _id: req.params.id }, (err, result) => {
        if (err) {
            return res.status(400).json({ success: false, error: err })
        }

        if (!result) {
            return res
                .status(404)
                .json({ success: false, error: `discount not found` })
        }
        return res.status(200).json({ success: true, id: result._id })
    }).catch(err => console.log(err))
}

let addDiscount = async(req, res) => {
    var discount = new DiscountModel(req.body)

    await discount.save()
        .then(() => {
            console.log()
            res.status(200).json({
                success: true,
                'discount': discount
            });
        })
        .catch(err => {
            res.status(400).json({ success: false, error: err })
        });
}

module.exports = {
    getDiscounts,
    addDiscount,
    getDiscountbyId,
    updateDiscount,
    deleteDiscount
}