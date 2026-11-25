// Optional CPU feature probe is unavailable in this synthetic Workers fixture.
module.exports = () => { throw new Error('optional native CPU probe unavailable'); };
