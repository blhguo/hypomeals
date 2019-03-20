$(function() {
    let keys = [
        "g h",
        "g s k",
        "g i n",
        "g p l",
        "g f",
        "###",
        "g l",
        "g g",
        "g s c",
        "g i m",
        "###",
        "###",
    ];
    let elements = $("ul.navbar-nav a");
    elements.each(function(i, el) {
        if (i >= keys.length) return;
        if (keys[i] === "###") return;
        console.log("Binding", keys[i], "to", $(el).attr("href"));
        Mousetrap.bind(keys[i], function(ev) {
            window.location.href = $(el).attr("href");
        })
    });
});