const { KeywordModel } = require('../model')

let getKeywords = async (req, res) => {
    await KeywordModel.find()
        .then(result => {
            return res.status(200).json({ success: true, data: result })
        })
        .catch( err => {
            return res.status(400).json({ success: false, error: err })
        })
}

let getKeywordbyId = async (req, res) => {
    await KeywordModel.findOne({ _id: req.params.id }, (err, keyword) => {
        if (err) {
            return res.status(400).json({ success: false, error: err })
        }

        if (!keyword) {
            return res
                .status(404)
                .json({ success: false, error: `keyword not found` })
        }
        return res.status(200).json({ success: true, data: keyword })
    }).catch(err => console.log(err))
}

let updateKeyword = async (req, res) => {
    KeywordModel.findOne({ _id: req.params.id }, (err, result) => {
        if (err) {
            return res.status(404).json({
                err,
                message: 'keyword not found!',
            })
        }
        result.keyword = req.body.keyword
        result.keyAlias = req.body.keyAlias
        result
            .save()
            .then(() => {
                return res.status(200).json({
                    success: true,
                    message: 'keyword updated!',
                    data: result
                })
            })
            .catch(error => {
                return res.status(404).json({
                    error,
                    message: 'keyword not updated!',
                })
            })
    })
}
let deleteKeyword = async (req, res) => {
    await KeywordModel.findOneAndDelete({ _id: req.params.id }, (err, result) => {
        if (err) {
            return res.status(400).json({ success: false, error: err })
        }

        if (!result) {
            return res
                .status(404)
                .json({ success: false, error: `Keyword not found` })
        }
        return res.status(200).json({ success: true, id: result._id })
    }).catch(err => console.log(err))
}

let addKeyword = async (req, res) => {
    var keyword = new KeywordModel(req.body)
    console.log("New Keyword: \n" + keyword)
    await keyword.save()
    .then(() => {
        console.log()
        res.status(200).json({
            success: true,
            'keyword': keyword
        });
    })
    .catch(err => {
        res.status(400).json({ success: false, error: err })
    });
}

module.exports = {
    getKeywords,
    addKeyword,
    getKeywordbyId,
    updateKeyword,
    deleteKeyword
}
