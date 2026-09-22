// 页面上的零碎交互

// 删除前确认
function chongfu_queren_shanchu() {
    var ge_ge = document.querySelectorAll(".btn-delete");
    ge_ge.forEach(function (an) {
        an.addEventListener("click", function (ev) {
            if (!confirm("确认要删除该条记录吗？此操作不可撤销。")) {
                ev.preventDefault();
            }
        });
    });
}

// 状态开关的确认弹窗
function kaiguan_queren() {
    var mo = document.getElementById("kaiguan-modal");
    if (!mo) { return; }
    var wen = document.getElementById("kaiguan-wen");
    var dai_ti_jiao = null;

    function guanbi() {
        mo.style.display = "none";
        dai_ti_jiao = null;
    }

    document.querySelectorAll(".kg-anniu").forEach(function (an) {
        an.addEventListener("click", function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            wen.textContent = an.getAttribute("data-queren") || "确定要改变该知识的状态吗？";
            dai_ti_jiao = an.getAttribute("data-biaodan");
            mo.style.display = "flex";
        });
    });

    document.getElementById("kaiguan-quxiao").addEventListener("click", guanbi);
    document.querySelector("#kaiguan-modal .modal-close").addEventListener("click", guanbi);

    // 确定后提交表单
    document.getElementById("kaiguan-queren").addEventListener("click", function () {
        var biao_id = dai_ti_jiao;
        guanbi();
        var biao = biao_id && document.getElementById(biao_id);
        if (biao) { biao.submit(); }
    });
}

function tishi_ziji_xiaoshi() {
    setTimeout(function () {
        var tiao = document.querySelectorAll(".flash");
        tiao.forEach(function (el) {
            el.style.transition = "opacity 0.5s";
            el.style.opacity = "0";
            setTimeout(function () {
                el.remove();
            }, 500);
        });
    }, 4000);
}

function sousuo_huiche_tijiao() {
    var kuang = document.querySelector("#searchKeyword");
    if (!kuang) {
        return;
    }
    kuang.addEventListener("keypress", function (ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            document.querySelector("#searchForm").submit();
        }
    });
}

document.addEventListener("DOMContentLoaded", function () {
    chongfu_queren_shanchu();
    kaiguan_queren();
    tishi_ziji_xiaoshi();
    sousuo_huiche_tijiao();
});
