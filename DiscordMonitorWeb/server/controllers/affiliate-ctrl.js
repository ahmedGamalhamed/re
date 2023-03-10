const { AffiliateModel } = require('../model')

let getAffiliates = async (req, res) => {
    await AffiliateModel.find()
        .then(result => {
            return res.status(200).json({ success: true, data: result })
        })
        .catch( err => {
            return res.status(400).json({ success: false, error: err })
        })
}

let getAffiliatebyId = async (req, res) => {
    await AffiliateModel.findOne({ _id: req.params.id }, (err, data) => {
        if (err) {
            return res.status(400).json({ success: false, error: err })
        }

        if (!data) {
            return res
                .status(404)
                .json({ success: false, error: `keyword not found` })
        }
        return res.status(200).json({ success: true, data: data })
    }).catch(err => console.log(err))
}

let updateAffiliate = async (req, res) => {
    await AffiliateModel.findOne({ _id: req.params.id }, (err, result) => {
        if (err) {
            return res.status(404).json({
                err,
                message: 'Affiliate not found!',
            })
        }
        result.storename = req.body.storename
        result.affiliate = req.body.affiliate
        result
            .save()
            .then(() => {
                return res.status(200).json({
                    success: true,
                    message: 'affiliate updated!',
                    data: req.body
                })
            })
            .catch(error => {
                return res.status(404).json({
                    error,
                    message: 'affiliate not updated!',
                })
            })
    })
}
let deleteAffiliate = async (req, res) => {
    await AffiliateModel.findOneAndDelete({ _id: req.params.id }, (err, result) => {
        if (err) {
            return res.status(400).json({ success: false, error: err })
        }

        if (!result) {
            return res
                .status(404)
                .json({ success: false, error: `affiliate not found` })
        }
        return res.status(200).json({ success: true, id: result._id })
    }).catch(err => console.log(err))
}

let addAffiliate = async (req, res) => {
    var affiliate = new AffiliateModel(req.body)
    await affiliate.save()
    .then(() => {
        res.status(200).json({
            success: true,
            'affiliate': affiliate
        });
    })
    .catch(err => {
        // console.log(err)
        res.status(400).json({ success: false, error: err })
    });
}

module.exports = {
    getAffiliates,
    addAffiliate,
    getAffiliatebyId,
    updateAffiliate,
    deleteAffiliate
}
